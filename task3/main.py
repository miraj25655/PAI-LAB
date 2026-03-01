
CAP_A = 4
CAP_B = 3
GOAL = 2

visited = set()
path = []

def dfs(state):
    a, b = state
    if a == GOAL:
        return True
    if state in visited:
        return False
    visited.add(state)

    rules = [
        ((CAP_A, b), "Fill Jug A"),
        ((a, CAP_B), "Fill Jug B"),
        ((0, b), "Empty Jug A"),
        ((a, 0), "Empty Jug B"),
        ((a - min(a, CAP_B - b), b + min(a, CAP_B - b)), "Pour Jug A -> Jug B"),
        ((a + min(b, CAP_A - a), b - min(b, CAP_A - a)), "Pour Jug B -> Jug A")
    ]

    for next_state, rule in rules:
        if next_state not in visited:
            path.append((state, rule, next_state))
            if dfs(next_state):
                return True
            path.pop()
    return False

start_state = (0, 0)
dfs(start_state)

print("Water Jug Problem Solution using DFS")
for i, step in enumerate(path, 1):
    print(f"Step {i}: {step[1]}")
    print(f"   State: {step[0]} -> {step[2]}")
print("Goal Reached: Jug A has 2 liters")
