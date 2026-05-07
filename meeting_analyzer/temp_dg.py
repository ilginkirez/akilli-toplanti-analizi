import jiwer, re
def n(t):
    t = t.lower()
    t = re.sub(r'\[[^\]]+\]', ' ', t)
    t = re.sub(r'\([^\)]+\)', ' ', t)
    t = re.sub(r"[^a-z0-9'\s]", ' ', t)
    return re.sub(r'\s+', ' ', t).strip()

ref = open('data/ami/reference/ES2016d_SpeakerA.txt', encoding='utf-8').read()
hyp = open('data/ami/results/deepgram_predicted.txt', encoding='utf-8').read()

w = jiwer.process_words(n(ref), n(hyp))
print(f'WER: {w.wer:.4f}, Ins: {w.insertions}, Del: {w.deletions}, Sub: {w.substitutions}')
