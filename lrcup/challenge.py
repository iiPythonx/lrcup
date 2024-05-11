# Adapted from:
# https://github.com/Dr-Blank/lrclibapi/blob/main/lrclib/cryptographic_challenge_solver.py

# Modules
import hashlib
import threading

# Solution class
class Solution:
    def __init__(self) -> None:
        self.nonce = None

    def is_solved(self) -> bool:
        return self.nonce is not None

def is_nonce_valid(prefix: str, nonce: int, target: bytes) -> bool:
    hash_value = hashlib.sha256(f"{prefix}{nonce}".encode()).digest()
    return hash_value < target

def find_nonce(
    prefix: str,
    target: bytes,
    solution: Solution,
    start: int,
    step: int
) -> Solution:
    nonce = start
    while not solution.is_solved():
        if is_nonce_valid(prefix, nonce, target):
            solution.nonce = nonce
            break

        nonce += step

    return solution

def solve(prefix: str, target: str) -> int:
    target, solution, threads = bytes.fromhex(target), Solution(), []
    for i in range(4):
        threads.append(threading.Thread(
            target = find_nonce,
            args = (prefix, target, solution, i, 4),
        ))

    [t.start() for t in threads]
    [t.join() for t in threads]
    return solution.nonce
