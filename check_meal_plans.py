import sqlite3

conn = sqlite3.connect('hospital.db')
c = conn.cursor()

# ✅ Fetch all meal plans
c.execute("SELECT * FROM meal_plans")
meal_plans = c.fetchall()
conn.close()

print("Stored Meal Plans:")
for plan in meal_plans:
    print(plan)
