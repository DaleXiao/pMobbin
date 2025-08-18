A python project to get files from Mobbin, code by Gemini, Codex, and Claude 4, no code by human, lol.

Recommend to deploy via Docker

### How to get api key?
1. Visit https://mobbin.com with your browser
2. Login with your account
3. Open devtool (F12)
4. Go to Network Tab
5. Refresh the page or take any other action on this page
6. Search for `apikey`, it normally looks like (sample below):
   ```
   eyJhxxxxxx............
   ```

### Install
Step 1: ```git clone https://github.com/DaleXiao/pMobbin ```

Step 2: Update the .env file with the token you get from browser

Step 3:
 ```docker-compose up -d --build ```


### Of you can to run it locally
```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```
#### How to use
##### 1. Login

###### User name / password
```bash
curl -X POST http://localhost:8085/api/login/password \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "password": "your-password"
  }'
```

###### OTP
```bash
# Send OTP
curl -X POST http://localhost:8085/api/login/send-otp \
  -H "Content-Type: application/json" \
  -d '{"email": "your-email@example.com"}'

# Verify
curl -X POST http://localhost:8085/api/login/verify \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "otp": "123456"
  }'
```

##### Search
```bash
curl http://localhost:8085/api/search?q=uber
```

### What I have done
Loggin - support both Google account SSO, and Email + Password login
Search - it's now able to fetch content from Mobbin.

Loggin with Email and Password
<img width="1332" height="303" alt="image" src="https://github.com/user-attachments/assets/9379e326-8671-4158-b088-185486520779" />

Search and get data
<img width="1338" height="383" alt="image" src="https://github.com/user-attachments/assets/5c2ed652-141f-461a-ba4e-95bf0df34704" />
