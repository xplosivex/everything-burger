import math
import random

def create_complex_calculation(num):
    operations = [
        # Addition-based combinations
        lambda x: f"({x//3} + {x//3} + {x-(2*(x//3))})",
        lambda x: f"({x//4} + {x//4} + {x//4} + {x-(3*(x//4))})",
        lambda x: f"({x//5} + {x//5} + {x//5} + {x//5} + {x-(4*(x//5))})",
        
        # Multiplication with division
        lambda x: f"({x*6} ÷ 2 ÷ 3)",
        lambda x: f"({x*12} ÷ 3 ÷ 4)",
        lambda x: f"({x*8} ÷ 2 ÷ 4)",
        lambda x: f"({x*15} ÷ 3 ÷ 5)",
        
        # Powers and roots combined
        lambda x: f"(√{x*x*4} ÷ 2)" if x <= 15 else f"({x-3} + 2 + 1)",
        lambda x: f"(2^{int(math.log2(x))} + {x - 2**int(math.log2(x))})",
        lambda x: f"(3^{int(math.log(x,3))} + {x - 3**int(math.log(x,3))})",
        
        # Mixed operations
        lambda x: f"(({x*3} ÷ 2) + ({x//2}))",
        lambda x: f"({x//5} × 4 + {x - 4*(x//5)})",
        lambda x: f"({x*2} ÷ 4 + {x//2} × 2)",
        lambda x: f"({x//3} × 6 - {x//2})",
        
        # Nested operations
        lambda x: f"((({x*2} ÷ 2) × 3) ÷ 3)",
        lambda x: f"(√{(x//2)*2 * (x//2)*2})" if x % 2 == 0 else f"({x-2} + 1 + 1)",
        lambda x: f"((({x*4} ÷ 4) × 2) ÷ 2)",
        lambda x: f"((({x//3} × 6) ÷ 2) × 1)",
        
        # Complex combinations
        lambda x: f"({x//6} × 3 + {x//3} × 2 + {x - (x//6)*3 - (x//3)*2})",
        lambda x: f"((√{(x//3)*(x//3)} × 3) + {x - (x//3)*3})" if x > 9 else f"({x-1} + 1)",
        lambda x: f"({x//8} × 4 + {x//4} × 2 + {x - (x//8)*4 - (x//4)*2})",
        lambda x: f"({x//2} × 3 - {x//3} × 2 + {x//6})",
        
        # Factorial-based (for small numbers)
        lambda x: f"(6 ÷ 2 × {x})" if x <= 10 else f"({x-1} + 1)",
        lambda x: f"(24 ÷ 6 × {x//4})" if x <= 20 else f"({x-2} + 2)",
        
        # Trigonometric (for variety)
        lambda x: f"(sin(90°) × {x})",
        lambda x: f"(cos(0°) × {x})"
    ]
    # Choose a random operation
    operation = random.choice(operations)
    return operation(num)
