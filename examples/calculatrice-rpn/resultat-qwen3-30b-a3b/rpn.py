def evaluate(expression):
    if not expression.strip():
        raise ValueError("Empty expression")
    stack = []
    tokens = expression.split()
    for token in tokens:
        if token in '+-*/':
            if len(stack) < 2:
                raise ValueError("Insufficient operands")
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
                    raise ValueError("Division by zero")
                stack.append(a / b)
        else:
            try:
                stack.append(float(token))
            except ValueError:
                raise ValueError(f"Unknown token '{token}'")
    if len(stack) != 1:
        raise ValueError("Multiple values left at end")
    return stack[0]

def main():
    import sys
    try:
        result = evaluate(sys.argv[1])
        print(result)
    except ValueError as e:
        print(f"Erreur : {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()