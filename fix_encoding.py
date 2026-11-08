input_file = "REPORT_LAB3.md"
output_file = "REPORT_LAB3_fixed.md"

with open(input_file, "r", encoding="utf-8") as f:
    broken_text = f.read()

# Відновлюємо байти, які були хибно інтерпретовані як cp1251, і розкодовуємо в utf-8
fixed_text = broken_text.encode("windows-1251", errors="replace").decode("utf-8", errors="replace")

with open(output_file, "w", encoding="utf-8") as f:
    f.write(fixed_text)

print("Файл успішно відновлено в:", output_file)