with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

assert 'AI Journal' not in html, 'Found AI Journal in HTML!'
assert 'id="btn-prediction-journal"' not in html, 'Found btn-prediction-journal!'
assert 'id="prediction-journal-modal"' not in html, 'Found prediction-journal-modal!'
assert 'openPredictionJournalModal' not in html, 'Found openPredictionJournalModal!'
assert 'loadPredictionJournal' not in html, 'Found loadPredictionJournal!'
print('ALL CHECKS PASSED: 0 UI traces of prediction journal in templates/index.html!')
