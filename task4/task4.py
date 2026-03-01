# N-Queens Problem (Dynamic) using Backtracking

def is_safe(board, row, col, n):
    for i in range(col):
        if board[row][i] == 1:
            return False

    i, j = row, col
    while i >= 0 and j >= 0:
        if board[i][j] == 1:
            return False
        i -= 1
        j -= 1

    i, j = row, col
    while i < n and j >= 0:
        if board[i][j] == 1:
            return False
        i += 1
        j -= 1

    return True


def solve_n_queens(board, col, n):
    if col >= n:
        return True

    for i in range(n):
        if is_safe(board, i, col, n):
            board[i][col] = 1

            if solve_n_queens(board, col + 1, n):
                return True

            board[i][col] = 0

    return False


def n_queens(n):
    board = [[0 for _ in range(n)] for _ in range(n)]

    if not solve_n_queens(board, 0, n):
        print("Solution does not exist")
        return

    for row in board:
        print(row)


# Dynamic input
if __name__ == "__main__":
    n = int(input("Enter value of N: "))
    n_queens(n)
