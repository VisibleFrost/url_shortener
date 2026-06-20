class Base62Converter:
    def __init__(self):
        self.alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        self.base = len(self.alphabet)
        self.char_to_map = {char: i for i, char in enumerate(self.alphabet)}
    
    def encode(self, number):
        if number == 0:
            return self.alphabet[0]
        res = []
        while number > 0:
            res.append(self.alphabet[number % self.base])
            number //= self.base
        return "".join(reversed(res))
    
    def decode(self, short_str):
        decimal_value = 0
        for char in short_str:
            if char not in self.char_to_map:
                raise ValueError(f"Недопустимый символ: {char}")
            decimal_value = decimal_value * self.base + self.char_to_map[char]
        return decimal_value
    
converter = Base62Converter()