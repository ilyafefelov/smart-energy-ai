import openpyxl
import pandas as pd

# Спробуємо з openpyxl (для xlsx)
try:
    # Спочатку спробуємо лютий
    print("=== ЛЮТИЙ 2026 ===")
    df_02 = pd.read_excel('data/raw/indexes_02.2026.xls', engine='openpyxl')
    print(f"✅ Лютий успішно завантажений!")
    print(f"Форма: {df_02.shape}")
    print(f"Колонки: {list(df_02.columns)}")
    print(df_02.head())
    
    df_02.to_csv('data/processed/hourly_prices_february_2026.csv', index=False)
    print("✅ Лютий збережений в CSV")
    
except Exception as e:
    print(f"❌ Ошибка з февралем: {e}")

# Спробуємо січень з ком іншою бібліотекою
try:
    print("\n=== СІЧЕНЬ 2026 ===")
    df_01 = pd.read_excel('data/raw/indexes_01.2026.xls', engine='openpyxl')
    print(f"✅ Січень успішно завантажений!")
    print(f"Форма: {df_01.shape}")
    print(f"Колонки: {list(df_01.columns)}")
    print(df_01.head())
    
    df_01.to_csv('data/processed/hourly_prices_january_2026.csv', index=False)
    print("✅ Січень збережений в CSV")
    
except Exception as e:
    print(f"❌ Ошибка зі січнем: {e}")
    print("\nСпробуємо читати як .xls через calamine...")
    try:
        df_01 = pd.read_excel('data/raw/indexes_01.2026.xls', engine='calamine')
        print("✅ Calamine спрацював!")
    except:
        print("❌ Calamine не допомогла. Файл може бути пошкоджений.")
