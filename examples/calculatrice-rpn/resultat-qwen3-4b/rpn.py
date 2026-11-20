#!/usr/bin/env python3
import sys

def evaluate(expression: str) -> float:
    stack = []
    tokens = expression.split()
    for token in tokens:
        if token in ['+', '-', '*', '/']:
            if len(stack) < 2:
                raise ValueError("Erreur : manque d'opérandes")
            b = stack.pop()
            a = stack.pop()
            if token == '+':
                stack.append(a + b)
            elif token == '-':
                stack.append(a - b)
            elif token == '*':
                stack.append(a * b)
            elif token == '/':
                if b == 0:
                    raise ValueError("Erreur : division par zéro")
                stack.append(a / b)
        else:
            try:
                num = float(token)
                stack.append(num)
            except ValueError:
                raise ValueError(f"Erreur : {token} n'est pas un nombre valide")
    if len(stack) != 1:
        raise ValueError("Erreur : trop d'opérandes restants")
    return stack[0]

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Erreur : Aucune expression RPN fournie.")
        sys.exit(1)
    try:
        result = evaluate(sys.argv[1])
        print(result)
    except ValueError as e:
        print(f"Erreur : {e}")
        sys.exit(1)