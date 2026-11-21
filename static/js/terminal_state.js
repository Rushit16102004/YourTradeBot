/**
 * static/js/terminal_state.js
 * Centralized Reactive State Store for NIFTY 50 Pro Terminal.
 * Provides a single source of truth for drawings, active tool, current user, and UI state.
 * Fully backwards-compatible with window.drawings, window.activeTool, and existing handlers.
 */
(function(window) {
    'use strict';

    const TerminalState = {
        _state: {
            drawings: [],
            selectedShapeId: null,
            activeTool: 'select',
            currentUser: null,
            timeframe: '5m',
            isSignalsEnabled: false
        },
        _listeners: {},

        on(event, callback) {
            if (!this._listeners[event]) this._listeners[event] = [];
            this._listeners[event].push(callback);
        },

        emit(event, data) {
            if (this._listeners[event]) {
                this._listeners[event].forEach(cb => {
                    try { cb(data); } catch(e) { console.error('TerminalState listener error:', e); }
                });
            }
        },

        get drawings() {
            return this._state.drawings;
        },

        set drawings(val) {
            this.setDrawings(val, { recordUndo: false, sync: false });
        },

        setDrawings(newDrawings, options = { recordUndo: true, sync: true }) {
            if (!Array.isArray(newDrawings)) return;
            if (options.recordUndo && typeof window.pushDrawingUndoSnapshot === 'function') {
                window.pushDrawingUndoSnapshot(this._state.drawings);
            }
            this._state.drawings = newDrawings;
            window.drawings = this._state.drawings; // Maintain global reference
            this.emit('drawings:change', this._state.drawings);
            if (options.sync && typeof window.saveDrawings === 'function') {
                window.saveDrawings();
            }
        },

        updateDrawing(id, updates) {
            const idx = this._state.drawings.findIndex(d => d.id === id);
            if (idx !== -1) {
                if (typeof window.pushDrawingUndoSnapshot === 'function') {
                    window.pushDrawingUndoSnapshot(this._state.drawings);
                }
                this._state.drawings[idx] = Object.assign({}, this._state.drawings[idx], updates);
                window.drawings = this._state.drawings;
                this.emit('drawings:change', this._state.drawings);
                if (typeof window.renderAllDrawings === 'function') window.renderAllDrawings();
                if (typeof window.saveDrawings === 'function') window.saveDrawings();
            }
        },

        deleteDrawing(id) {
            const beforeLen = this._state.drawings.length;
            const filtered = this._state.drawings.filter(d => d.id !== id);
            if (filtered.length !== beforeLen) {
                if (typeof window.pushDrawingUndoSnapshot === 'function') {
                    window.pushDrawingUndoSnapshot(this._state.drawings);
                }
                this._state.drawings = filtered;
                window.drawings = this._state.drawings;
                this.emit('drawings:change', this._state.drawings);
                if (typeof window.renderAllDrawings === 'function') window.renderAllDrawings();
                if (typeof window.saveDrawings === 'function') window.saveDrawings();
            }
        },

        get activeTool() {
            return this._state.activeTool;
        },

        setActiveTool(tool) {
            this._state.activeTool = tool;
            window.activeTool = tool;
            this.emit('tool:change', tool);
        },

        get currentUser() {
            return this._state.currentUser;
        },

        setCurrentUser(u) {
            this._state.currentUser = u;
            window.currentUser = u;
            this.emit('user:change', u);
        }
    };

    window.TerminalState = TerminalState;
})(window);
