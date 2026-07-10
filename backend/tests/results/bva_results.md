| Boundary Case | Sample File | Expected | Actual | Elapsed (ms) | Result | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Just under 25MB limit | under_limit.wav | 200 | 200 | 5283.7 | PASS | Got expected status 200. |
| At/near 25MB limit | at_limit.wav | 200 | 200 | 9875.2 | PASS | Got expected status 200. |
| Just over 25MB limit | over_limit.wav | 400 | 400 | 2221.9 | PASS | Got expected status 400. |
| Shortest possible clip (~0.3-0.5s) | shortest_clip.wav | 200 | 200 | 3055.2 | PASS | Got expected status 200. |
| Concurrent requests (n=5) | clear_speech.wav | 5/5 succeed | 5/5 | 7071.1 | PASS | 5/5 concurrent requests succeeded. |