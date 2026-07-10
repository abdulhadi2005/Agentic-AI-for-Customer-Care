| Input Class | Sample File | Expected | Actual Status | Result | Notes |
| --- | --- | --- | --- | --- | --- |
| Clear speech (valid) | clear_speech.wav | status=200 | 200 | PASS | Got 123 chars of transcript. |
| Speech + heavy background noise (valid) | noisy_speech.wav | status=200 | 200 | PASS | Got 119 chars of transcript. |
| Silence / muted audio (valid input, no speech) | silence.wav | status=200 | 200 | PASS | Correctly returned empty transcript (no hallucinated text). |
| Non-speech audio — music/tone (valid input, no speech) | non_speech_music.wav | status=200 | 200 | PASS | Correctly returned empty transcript (no hallucinated text). |
| Corrupted/malformed audio file (invalid) | corrupted.mp3 | status=500 | 500 | PASS | Server correctly rejected with 500: {'detail': 'Transcription engine failed.'} |
| Wrong file type — not audio at all (invalid) | wrong_type.txt | status=400 | 400 | PASS | Server correctly rejected with 400: {'detail': 'Unsupported audio type: text/plain'} |