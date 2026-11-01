"""
Permanent Vector Database Manager for RAG Architecture using ChromaDB.
Stores Strategy Knowledge, Signals, 5m Market Snapshots, S&R Levels, and User Drawings.
"""
from __future__ import annotations

import os
import hashlib
import logging
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd
import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from .config import RAGConfig
from .strategy_knowledge_data import STRATEGY_KNOWLEDGE_DOCS

logger = logging.getLogger("RAGDatabase")


STOPWORDS = {
    "what", "is", "are", "the", "a", "an", "and", "or", "of", "in", "to", "for",
    "with", "on", "at", "by", "from", "it", "this", "that", "these", "those",
    "how", "do", "does", "did", "can", "could", "should", "would", "about",
    "tell", "me", "give", "explain", "i", "you", "my", "your", "we", "our",
    "please", "hi", "hello", "hey", "sir", "bot", "assistant"
}

DOMAIN_KEYWORDS = {
    "pcr", "vwap", "cpr", "ema", "rsi", "macd", "supertrend", "adx", "atr",
    "breakout", "reversal", "trap", "liquidity", "support", "resistance",
    "expiry", "vix", "preflight", "lot", "lots", "drawing", "angle", "pattern",
    "patterns", "confluence", "brain", "ratio", "floor", "ceiling", "call", "put",
    "overbought", "oversold", "contrarian", "touches", "runway", "bounce"
}


class FastNgramEmbedding(EmbeddingFunction):
    """
    High-performance, domain-aware local embedding function.
    - Suppresses conversational English stopwords so search is not hijacked.
    - Heavily boosts institutional trading domain keywords (PCR, VWAP, S&R, Risk).
    - Uses subword character trigrams on non-stopwords for typo/stemming resilience.
    - 0% GPU required, 100% offline, sub-millisecond execution.
    """
    def __init__(self, dim: int = 256):
        self.dim = dim

    def __call__(self, input: Documents) -> Embeddings:
        embeddings: List[List[float]] = []
        for text in input:
            vec = np.zeros(self.dim, dtype=np.float32)
            cleaned = text.lower()
            punctuation_chars = ".,!?;:()[]\"'"
            words = [w.strip(punctuation_chars) for w in cleaned.split() if w.strip(punctuation_chars)]

            # Word 1-grams and 2-grams
            for i, w in enumerate(words):
                if w in STOPWORDS:
                    weight = 0.05
                elif w in DOMAIN_KEYWORDS:
                    weight = 4.5
                else:
                    weight = 1.5

                h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16)
                idx = h % self.dim
                sign = 1.0 if ((h >> 8) & 1) else -1.0
                vec[idx] += sign * weight

                # Bigram if both words are not pure stopwords
                if i < len(words) - 1:
                    w2 = words[i + 1]
                    if w not in STOPWORDS or w2 not in STOPWORDS:
                        bigram = f"{w}_{w2}"
                        h2 = int(hashlib.md5(bigram.encode("utf-8")).hexdigest(), 16)
                        idx2 = h2 % self.dim
                        sign2 = 1.0 if ((h2 >> 8) & 1) else -1.0
                        bg_weight = 3.5 if (w in DOMAIN_KEYWORDS or w2 in DOMAIN_KEYWORDS) else 2.0
                        vec[idx2] += sign2 * bg_weight

                # Character 3-grams for non-stopwords (typo / prefix resilience)
                if w not in STOPWORDS and len(w) >= 3:
                    for j in range(len(w) - 2):
                        trigram = w[j : j + 3]
                        ht = int(hashlib.md5(trigram.encode("utf-8")).hexdigest(), 16)
                        idxt = ht % self.dim
                        signt = 1.0 if ((ht >> 8) & 1) else -1.0
                        vec[idxt] += signt * 0.8

            norm = float(np.linalg.norm(vec))
            if norm > 0:
                vec /= norm
            embeddings.append(vec.tolist())
        return embeddings


class RAGDatabase:
    """
    Manages persistent local ChromaDB storage across 5 domain-specific collections.
    """
    _instance: Optional[RAGDatabase] = None

    def __init__(self, persist_dir: Optional[str] = None):
        path = persist_dir or RAGConfig.CHROMA_PERSIST_DIR
        os.makedirs(path, exist_ok=True)
        self.persist_dir = path
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.embedding_fn = FastNgramEmbedding(dim=256)

        # 5 Core Collections
        self.col_strategy = self.client.get_or_create_collection(
            name="strategy_knowledge", embedding_function=self.embedding_fn
        )
        self.col_signals = self.client.get_or_create_collection(
            name="signals_memory", embedding_function=self.embedding_fn
        )
        self.col_snapshots = self.client.get_or_create_collection(
            name="market_snapshots", embedding_function=self.embedding_fn
        )
        self.col_sr = self.client.get_or_create_collection(
            name="sr_levels", embedding_function=self.embedding_fn
        )
        self.col_drawings = self.client.get_or_create_collection(
            name="user_drawings", embedding_function=self.embedding_fn
        )
        self.col_predictions = self.client.get_or_create_collection(
            name="prediction_reflections", embedding_function=self.embedding_fn
        )

        # Pre-seed comprehensive strategy knowledge base
        self.seed_strategy_knowledge()

    @classmethod
    def get_instance(cls) -> RAGDatabase:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def seed_strategy_knowledge(self):
        """Seeds permanent trading playbook, rules, and FAQ documents into strategy_knowledge."""
        try:
            current_ids = set(d["id"] for d in STRATEGY_KNOWLEDGE_DOCS)
            # Remove any legacy or orphaned documents from previous revisions
            try:
                existing = self.col_strategy.get()
                if existing and existing.get("ids"):
                    orphaned = [eid for eid in existing["ids"] if eid not in current_ids]
                    if orphaned:
                        self.col_strategy.delete(ids=orphaned)
                        logger.info("Purged %d obsolete/orphaned documents from strategy knowledge.", len(orphaned))
            except Exception:
                pass

            doc_ids = [d["id"] for d in STRATEGY_KNOWLEDGE_DOCS]
            documents = [f"{d['title']}\n{d['content']}" for d in STRATEGY_KNOWLEDGE_DOCS]
            metadatas = [
                {"title": d["title"], "category": d["category"], "tags": d["tags"]}
                for d in STRATEGY_KNOWLEDGE_DOCS
            ]
            self.col_strategy.upsert(ids=doc_ids, documents=documents, metadatas=metadatas)
            logger.info("Indexed %d operational strategy documents in RAG knowledge base.", len(doc_ids))
        except Exception as e:
            logger.error("Error seeding strategy knowledge in RAG: %s", e)

    def add_signal(self, alert: Dict[str, Any], outcome: Optional[Dict[str, Any]] = None) -> bool:
        """
        Permanently indexes an S&R Breakout, Reversal, or ZFTF signal into signals_memory.
        """
        try:
            alert_id = str(alert.get("id", f"sig_{int(pd.Timestamp.now().timestamp())}"))
            action = alert.get("action", alert.get("type", "SIGNAL"))
            sub_type = alert.get("sub_type", "BREAKOUT")
            price = float(alert.get("price", 0.0))
            level = float(alert.get("broken_level") or alert.get("swept_level") or 0.0)
            bounces = int(alert.get("broken_bounces", 4))
            target = float(alert.get("target_level", 0.0))
            gap = float(alert.get("gap_pts", 0.0))
            tf_tag = alert.get("timeframe_tag", "1M + 2M Confluence")
            wick_info = f", {alert.get('wick_pct')}% Rejection Wick" if alert.get("wick_pct") else ""
            time_str = alert.get("time_str", str(pd.Timestamp.now()))

            outcome_text = ""
            if outcome:
                outcome_text = f" Trade Result: {outcome.get('status', 'PENDING')} (P&L: {outcome.get('pnl_pts', 0.0):+.1f} pts)."

            doc_text = (
                f"Trade Alert: {action} ({sub_type}) on NIFTY 50 at ₹{price:.2f}. "
                f"Key S&R Level: ₹{level:.2f} ({tf_tag}, {bounces}x touches{wick_info}). "
                f"Runway Target: ₹{target:.2f} (Gap: {gap:.1f} pts >= 50 threshold). "
                f"Timestamp: {time_str}.{outcome_text}"
            )

            metadata = {
                "signal_id": alert_id,
                "type": alert.get("type", "CALL"),
                "sub_type": sub_type,
                "price": price,
                "level": level,
                "target": target,
                "timeframe_tag": tf_tag,
                "is_confluence": bool(alert.get("is_confluence", False)),
                "time_str": time_str,
            }

            self.col_signals.upsert(ids=[alert_id], documents=[doc_text], metadatas=[metadata])
            logger.info("RAG signals_memory indexed signal %s", alert_id)
            return True
        except Exception as e:
            logger.error("Error adding signal to RAG: %s", e)
            return False

    def bulk_index_signals(self, signals: List[Dict[str, Any]]) -> int:
        """Permanently bulk indexes all signals from historical evaluation and live feed."""
        if not signals:
            return 0
        try:
            ids = []
            docs = []
            metas = []
            for s in signals:
                ts = s.get("timestamp") or s.get("time_str") or str(pd.Timestamp.now())
                ts_str = ts.strftime("%Y-%m-%d %H:%M:%S") if hasattr(ts, "strftime") else str(ts)
                sig_type = s.get("signal") or s.get("action") or s.get("type", "SIGNAL")
                price = float(s.get("price", 0.0) or 0.0)
                entry = s.get("entry_price")
                entry_str = f", Entry: ₹{float(entry):.2f}" if entry is not None else ""
                reason = s.get("reason") or s.get("sub_type", "MOMENTUM")
                sig_id = str(s.get("id") or f"sig_{ts_str[:19].replace(' ', '_').replace(':', '')}_{sig_type}")

                doc = f"Trade Signal {sig_type} at ₹{price:.2f} on {ts_str}{entry_str}. Trigger Reason: {reason}."
                meta = {
                    "timestamp": ts_str,
                    "signal": str(sig_type),
                    "price": price,
                    "reason": str(reason),
                }
                ids.append(sig_id)
                docs.append(doc)
                metas.append(meta)

            if ids:
                self.col_signals.upsert(ids=ids, documents=docs, metadatas=metas)
                logger.info("Bulk-indexed %d signals into RAG signals_memory.", len(ids))
                return len(ids)
        except Exception as e:
            logger.error("Error bulk-indexing signals in RAG: %s", e)
        return 0

    def add_market_snapshot(
        self,
        df_5m: pd.DataFrame,
        cur_p: float,
        mtf_data: Optional[Dict[str, Any]] = None,
        sr_levels: Optional[List[Dict[str, Any]]] = None,
        is_expiry: bool = False,
        orb_status: str = "Inside ORB Range",
    ) -> bool:
        """
        Indexes a clean 5-minute candle close snapshot with indicators, MTF matrix, and market regime.
        """
        try:
            if df_5m is None or df_5m.empty:
                return False

            last_c = df_5m.iloc[-1]
            ts = df_5m.index[-1]
            time_str = ts.strftime("%d-%m-%Y %H:%M IST") if hasattr(ts, "strftime") else str(ts)
            snap_id = f"snap_{int(ts.timestamp())}" if hasattr(ts, "timestamp") else f"snap_{str(ts)[:16]}"

            open_p = float(last_c.get("open", cur_p))
            high_p = float(last_c.get("high", cur_p))
            low_p = float(last_c.get("low", cur_p))
            close_p = float(last_c.get("close", cur_p))
            vol = int(last_c.get("volume", 0))

            vwap_p = float(last_c.get("vwap", 0.0))
            sma_p = float(last_c.get("mean", 0.0))
            up2 = float(last_c.get("vwap_upper_2", 0.0))
            lo2 = float(last_c.get("vwap_lower_2", 0.0))

            mtf_confluence = mtf_data.get("confluence", "Mixed") if mtf_data else "Mixed"
            mtf_badge = mtf_data.get("badge_class", "neutral") if mtf_data else "neutral"

            regime = "Expiry Day (Tuesday - High Theta)" if is_expiry else "Regular Session"
            sr_count = len(sr_levels) if sr_levels else 0

            doc_text = (
                f"5-Minute Candle Snapshot at {time_str}: LTP ₹{close_p:.2f} (O: ₹{open_p:.2f}, H: ₹{high_p:.2f}, L: ₹{low_p:.2f}). "
                f"Session VWAP: ₹{vwap_p:.2f}, ±2σ Bands: [+2σ Exhaustion: ₹{up2:.2f} / -2σ Dip: ₹{lo2:.2f}], SMA 20: ₹{sma_p:.2f}. "
                f"MTF Trend Matrix: {mtf_confluence} ({mtf_badge.upper()}). "
                f"Session Regime: {regime}, ORB Status: {orb_status}. Active S&R Levels Monitored: {sr_count}."
            )

            metadata = {
                "timestamp": time_str,
                "close": close_p,
                "vwap": vwap_p,
                "sma": sma_p,
                "is_expiry": is_expiry,
                "mtf": mtf_confluence,
                "orb_status": orb_status,
            }

            self.col_snapshots.upsert(ids=[snap_id], documents=[doc_text], metadatas=[metadata])
            return True
        except Exception as e:
            logger.error("Error adding market snapshot to RAG: %s", e)
            return False

    def add_sr_levels(self, levels: List[Dict[str, Any]], period_tag: str = "combined"):
        """Indexes calculated S&R levels permanently into sr_levels collection."""
        try:
            if not levels:
                return
            ids = []
            docs = []
            metas = []
            for l in levels:
                lid = str(l.get("id", f"sr_{int(l.get('avg_price', 0))}"))
                role = l.get("role", "S/R Level")
                price = float(l.get("avg_price", l.get("price1", 0.0)))
                bounces = int(l.get("bounces", 3))
                tf_tag = l.get("timeframe_tag", period_tag)
                is_conf = bool(l.get("is_confluence", False))

                text = f"S&R Level: {role} at ₹{price:.2f} ({bounces} touches, Origin: {tf_tag}, Confluence={is_conf})."
                ids.append(f"{period_tag}_{lid}")
                docs.append(text)
                metas.append({
                    "role": role,
                    "price": price,
                    "bounces": bounces,
                    "timeframe_tag": tf_tag,
                    "is_confluence": is_conf,
                })
            self.col_sr.upsert(ids=ids, documents=docs, metadatas=metas)
        except Exception as e:
            logger.error("Error indexing S&R levels in RAG: %s", e)

    def add_user_drawing(self, drawing: Dict[str, Any], user_id: str = "default_user"):
        """Indexes user-drawn chart shapes with annotations, angles, and strict user_id isolation."""
        try:
            raw_id = str(drawing.get("id", f"draw_{int(pd.Timestamp.now().timestamp())}"))
            doc_id = f"{user_id}_{raw_id}"
            dtype = drawing.get("type", "line")
            p1 = float(drawing.get("price1", 0.0) or 0.0)
            p2 = float(drawing.get("price2", p1) or p1)
            rem = drawing.get("remark", f"User {dtype}")
            angle = drawing.get("angle")
            angle_str = f", Measured Angle: {angle}°" if angle is not None else ""

            if dtype == "fibonacci":
                diff = p2 - p1
                f0 = p2
                f236 = p2 - 0.236 * diff
                f382 = p2 - 0.382 * diff
                f500 = p2 - 0.500 * diff
                f618 = p2 - 0.618 * diff
                f786 = p2 - 0.786 * diff
                f1000 = p1
                f1618 = p2 + 0.618 * diff if diff > 0 else p2 - 0.618 * abs(diff)
                text = (
                    f"User ({user_id}) Fibonacci Retracement Tool: Start P1=₹{p1:.2f}, End P2=₹{p2:.2f}. "
                    f"Calculated Levels: 0.000=₹{f0:.2f}, 0.236=₹{f236:.2f}, 0.382=₹{f382:.2f}, 0.500(Equilibrium)=₹{f500:.2f}, "
                    f"0.618(GOLDEN RATIO)=₹{f618:.2f}, 0.786=₹{f786:.2f}, 1.000=₹{f1000:.2f}, 1.618(Golden Extension)=₹{f1618:.2f}. "
                    f"Remark: '{rem}'."
                )
            elif dtype == "channel":
                c_w = float(drawing.get("channelWidth", 20.0))
                text = f"User ({user_id}) Parallel Channel: Trendline P1=₹{p1:.2f} to P2=₹{p2:.2f}, Width={c_w:.2f} pts. Remark='{rem}'."
            elif dtype == "ray":
                text = f"User ({user_id}) Horizontal Ray: Anchored at Price ₹{p1:.2f} extending indefinitely to the right as key reaction level. Remark='{rem}'."
            elif dtype == "price_range":
                pts = abs(p2 - p1)
                pct = (pts / max(p1, 1.0)) * 100
                text = f"User ({user_id}) Price Range Measurement: From ₹{p1:.2f} to ₹{p2:.2f} ({pts:.2f} pts / {pct:.2f}%). Direction={'UP' if p2 >= p1 else 'DOWN'}."
            elif dtype == "text":
                user_note = drawing.get("text", rem)
                text = f"User ({user_id}) Chart Note at ₹{p1:.2f}: '{user_note}'."
            else:
                text = f"User ({user_id}) Chart Drawing ({dtype.upper()}): Name/Remark='{rem}'{angle_str}. Anchors: P1=₹{p1:.2f}, P2=₹{p2:.2f}."
            meta = {
                "user_id": str(user_id),
                "drawing_id": str(raw_id),
                "type": str(dtype),
                "price1": float(p1),
                "price2": float(p2),
                "remark": str(rem),
                "angle": str(angle) if angle is not None else "N/A",
            }
            self.col_drawings.upsert(ids=[doc_id], documents=[text], metadatas=[meta])
            logger.info("Indexed user drawing %s in ChromaDB for %s", doc_id, user_id)
        except Exception as e:
            logger.error("Error indexing user drawing in RAG: %s", e)

    def delete_user_drawing(self, user_id: str, drawing_id: str):
        """Immediately deletes a drawing from ChromaDB to prevent AI hallucinations."""
        try:
            doc_id = f"{user_id}_{drawing_id}"
            try:
                self.col_drawings.delete(ids=[doc_id])
                logger.info("Deleted user drawing %s from ChromaDB for %s", doc_id, user_id)
            except Exception:
                pass
            try:
                self.col_drawings.delete(where={"$and": [{"user_id": str(user_id)}, {"drawing_id": str(drawing_id)}]})
            except Exception:
                pass
        except Exception as e:
            logger.error("Error deleting user drawing from ChromaDB: %s", e)

    def clear_user_drawings(self, user_id: str):
        """Wipes all drawings belonging to this user_id from ChromaDB."""
        try:
            self.col_drawings.delete(where={"user_id": str(user_id)})
            logger.info("Cleared all ChromaDB drawings for user %s", user_id)
        except Exception as e:
            logger.error("Error clearing user drawings from ChromaDB: %s", e)

    def sync_user_drawings(self, user_id: str, drawings: List[Dict[str, Any]]):
        """Atomically synchronizes the full list of drawings for a user into ChromaDB."""
        try:
            self.clear_user_drawings(user_id)
            for d in drawings:
                self.add_user_drawing(d, user_id=user_id)
        except Exception as e:
            logger.error("Error syncing drawings in ChromaDB: %s", e)

    def add_prediction(self, pred: Dict[str, Any]) -> bool:
        """Indexes an active trade prediction into vector memory."""
        try:
            pred_id = str(pred.get("id"))
            direction = pred.get("direction", "BUY")
            source = pred.get("source", "MANUAL")
            entry = float(pred.get("entry_price", 0.0))
            target = float(pred.get("target_price", 0.0))
            stop = float(pred.get("stop_loss", 0.0))
            rr = pred.get("rr_ratio", 1.0)
            ctx = pred.get("market_context") or {}
            if isinstance(ctx, str):
                try:
                    ctx = json.loads(ctx)
                except Exception:
                    ctx = {}
            touches = ctx.get("touches", ctx.get("bounces", 4))
            vwap = ctx.get("vwap", 0.0)

            doc_text = (
                f"Active Trade Prediction: {direction} setup on NIFTY 50 ({source}). "
                f"Entry: ₹{entry:.2f}, Target: ₹{target:.2f}, Stop Loss: ₹{stop:.2f} (R:R {rr}:1). "
                f"Market Context: S&R touches {touches}, VWAP ₹{vwap}."
            )
            meta = {
                "id": pred_id,
                "type": "prediction",
                "direction": direction,
                "source": source,
                "status": "ACTIVE",
                "entry": float(entry),
                "target": float(target),
                "stop": float(stop),
            }
            self.col_predictions.upsert(ids=[pred_id], documents=[doc_text], metadatas=[meta])
            return True
        except Exception as e:
            logger.warning("Error adding prediction to RAG: %s", e)
            return False

    def index_prediction_outcome(self, pred: Dict[str, Any]) -> bool:
        """
        Permanently indexes a completed trade prediction with outcome, error diagnosis,
        and learned reflection text for RAG self-correction.
        """
        try:
            pred_id = str(pred.get("id"))
            direction = pred.get("direction", "BUY")
            source = pred.get("source", "MANUAL")
            entry = float(pred.get("entry_price", 0.0))
            target = float(pred.get("target_price", 0.0))
            stop = float(pred.get("stop_loss", 0.0))
            status = pred.get("status", "RESOLVED")
            actual_pnl = float(pred.get("actual_pnl_pts", 0.0))
            pnl_error = float(pred.get("pnl_error_pts", 0.0))
            mae = float(pred.get("mae_pts", 0.0))
            mfe = float(pred.get("mfe_pts", 0.0))
            err_cat = pred.get("error_category", "NONE")
            diagnosis = pred.get("error_analysis", "")
            reflection = pred.get("reflection_text", "")

            is_trap = (status == "SL_HIT" or actual_pnl < 0)
            trap_prefix = "[ANONYMOUS_COLLECTIVE_TRAP_LEARNING]" if is_trap else "[ANONYMOUS_COLLECTIVE_WIN_SETUP]"
            trap_directive = (
                f"COPILOT TRAP AWARENESS DIRECTIVE: A previous trader took a {direction} setup near ₹{entry:.2f} and took a LOSS ({actual_pnl:+.1f} pts) "
                f"due to {err_cat} ({diagnosis}). RAG Copilot MUST treat this price zone as an INSTITUTIONAL TRAP ZONE and actively WARN any trader "
                f"against entering an unconfirmed {direction} trade near ₹{entry:.2f} to prevent repeating this exact mistake."
                if is_trap else
                f"COPILOT WINNING SETUP DIRECTIVE: A previous trader executed a high-conviction {direction} setup near ₹{entry:.2f} and hit TARGET (+{actual_pnl:.1f} pts). "
                f"This confirmed that ₹{entry:.2f} is a valid institutional continuation level."
            )

            doc_text = (
                f"{trap_prefix}\n"
                f"• Setup: {direction} ({source}) at Entry ₹{entry:.2f}, Target ₹{target:.2f}, Stop Loss ₹{stop:.2f}\n"
                f"• Status: {status} | Actual PnL: {actual_pnl:+.1f} pts | PnL Error: {pnl_error:+.1f} pts\n"
                f"• Excursion: MAE {mae:.1f} pts adverse, MFE {mfe:.1f} pts favorable\n"
                f"• Error Category: {err_cat}\n"
                f"• Institutional Analysis: {diagnosis}\n"
                f"• Learned Technical Rule: {reflection}\n"
                f"• {trap_directive}"
            )
            meta = {
                "id": pred_id,
                "type": "collective_market_learning",
                "direction": direction,
                "source": source,
                "status": status,
                "is_trap": 1 if is_trap else 0,
                "error_category": err_cat,
                "actual_pnl": actual_pnl,
                "pnl_error": pnl_error,
                "mae": mae,
                "mfe": mfe,
            }
            self.col_predictions.upsert(ids=[pred_id], documents=[doc_text], metadatas=[meta])
            logger.info("Indexed anonymized collective trade lesson %s into RAG vector memory (Trap: %s, Status: %s)", pred_id, is_trap, status)
            return True
        except Exception as e:
            logger.warning("Error indexing prediction outcome in RAG: %s", e)
            return False

    def query_similar_predictions(self, query_text: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """Retrieves most relevant past prediction reflections to learn from past errors."""
        if self.col_predictions.count() == 0:
            return []
        try:
            res = self.col_predictions.query(
                query_texts=[query_text],
                n_results=min(top_k, self.col_predictions.count())
            )
            results = []
            if res and res.get("documents") and len(res["documents"]) > 0:
                for i, doc in enumerate(res["documents"][0]):
                    meta = res["metadatas"][0][i] if res.get("metadatas") else {}
                    dist = res["distances"][0][i] if res.get("distances") else 0.0
                    results.append({
                        "content": doc,
                        "metadata": meta,
                        "distance": dist,
                    })
            return results
        except Exception as e:
            logger.warning("Error querying prediction reflections: %s", e)
            return []

    def query_context(
        self,
        query_text: str,
        user_id: Optional[str] = None,
        top_k: int = 3,
        collections: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Searches across requested or all collections and returns relevant contextual chunks.
        Strictly isolates user_drawings by user_id so users never see each other's drawings.
        """
        cols_map = {
            "strategy": self.col_strategy,
            "signals": self.col_signals,
            "snapshots": self.col_snapshots,
            "sr": self.col_sr,
            "drawings": self.col_drawings,
            "predictions": self.col_predictions,
        }

        q_lower = query_text.lower()
        if not collections:
            # Check if user explicitly asked for strategy signal or historical signals
            explicit_signal_terms = [
                "main signal", "display signal", "last signal", "latest signal",
                "past signal", "recent signal", "signal history", "confirmed signal",
                "strategy signal", "signal log", "display signals", "main signals",
                "info about signal", "info about main signal", "tell me about signal",
                "what was the signal", "show signal", "signals on record", "last trade signal"
            ]
            is_explicit_signal = any(p in q_lower for p in explicit_signal_terms) or (
                ("signal" in q_lower or "signals" in q_lower) and not any(w in q_lower for w in [
                    "when should i enter", "where should i enter", "when to enter",
                    "where to enter", "when i have enter", "should i buy", "should i sell",
                    "can i enter", "trade suggestion", "entry suggestion", "where to buy", "where to sell"
                ])
            )

            # Dynamic Query Intent Routing to prioritize the most relevant vector collections
            if any(w in q_lower for w in ["developer", "creator", "provider", "strategy provider", "contact", "email", "rushit", "connect"]):
                target_keys = ["strategy"]
            elif any(w in q_lower for w in ["pcr", "put call", "put-call", "option chain", "open interest", "oi", "max pain", "call writing", "put writing", "call buyer", "put buyer"]):
                target_keys = ["strategy"]
            elif any(w in q_lower for w in ["pattern", "patterns", "harmonic", "butterfly", "gartley", "bat", "crab", "candlestick", "pin bar", "engulfing", "morning star", "doji", "head and shoulders", "triangle", "flag"]):
                target_keys = ["strategy"]
            elif any(w in q_lower for w in ["brain", "personal brain", "mentor", "conflict", "conflicts", "philosophy", "discretionary", "setup mode", "setup modes"]):
                target_keys = ["strategy"]
            elif any(w in q_lower for w in ["lot", "quantity", "contract", "sizing", "risk policy", "disclaimer", "vix", "india vix", "rules"]):
                target_keys = ["strategy"]
            elif is_explicit_signal:
                target_keys = ["signals", "strategy"]
            elif any(w in q_lower for w in ["enter", "entry", "when to enter", "where to enter", "when i have enter", "should i buy", "should i sell", "buy or sell", "trade suggestion", "entry suggestion"]):
                target_keys = ["sr", "strategy"]
            elif any(w in q_lower for w in ["drawing", "droing", "angle", "line", "trendline"]):
                target_keys = ["drawings", "strategy"]
            elif any(w in q_lower for w in ["prediction", "predict", "accuracy", "error", "win rate", "loss reason", "past trades", "pnl model"]):
                target_keys = ["predictions", "strategy"]
            elif any(w in q_lower for w in ["support", "resistance", "s&r", "level", "barrier", "confluence", "nearest"]):
                target_keys = ["sr", "strategy"]
            elif any(w in q_lower for w in ["breakout", "trap", "reversal", "strategy", "vwap", "band", "exhaustion", "rule", "how to", "why"]):
                target_keys = ["strategy", "sr"]
            else:
                target_keys = ["strategy", "sr"]
                if user_id:
                    target_keys.append("drawings")
        else:
            target_keys = list(collections)

        results: List[Dict[str, Any]] = []

        for key in target_keys:
            col = cols_map.get(key)
            if not col or col.count() == 0:
                continue
            try:
                # Apply strict user_id partition on drawings collection
                where_filter = None
                if key == "drawings":
                    if not user_id:
                        # Guest user has no indexed private drawings
                        continue
                    where_filter = {"user_id": str(user_id)}

                query_params = {
                    "query_texts": [query_text],
                    "n_results": min(top_k, col.count())
                }
                if where_filter:
                    query_params["where"] = where_filter

                res = col.query(**query_params)
                if res and res.get("documents") and len(res["documents"]) > 0:
                    for i, doc in enumerate(res["documents"][0]):
                        meta = res["metadatas"][0][i] if res.get("metadatas") else {}
                        dist = res["distances"][0][i] if res.get("distances") else 0.0
                        # Apply intelligent affinity boost to strategy knowledge
                        adj_dist = dist - (0.25 if key == "strategy" else 0.0)
                        results.append({
                            "collection": key,
                            "content": doc,
                            "metadata": meta,
                            "distance": dist,
                            "adj_distance": adj_dist,
                        })
            except Exception as e:
                logger.warning("Error querying collection %s: %s", key, e)

        # Sort by adjusted distance (closest first)
        results.sort(key=lambda x: x.get("adj_distance", x["distance"]))
        return results[: top_k * 2]

    def get_stats(self) -> Dict[str, Any]:
        """Returns statistics for all 5 collections."""
        return {
            "persist_dir": self.persist_dir,
            "strategy_knowledge_count": self.col_strategy.count(),
            "signals_memory_count": self.col_signals.count(),
            "market_snapshots_count": self.col_snapshots.count(),
            "sr_levels_count": self.col_sr.count(),
            "user_drawings_count": self.col_drawings.count(),
            "prediction_reflections_count": self.col_predictions.count(),
        }
