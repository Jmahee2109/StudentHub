# StudentHub

## Running the application

Set a session secret and choose an initial admin password before starting the app:

```bash
export STUDENTHUB_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export STUDENTHUB_ADMIN_PASSWORD='choose-a-strong-password'
python app.py
```

The initial admin account uses `admin@studenthub.com` and the password supplied
through `STUDENTHUB_ADMIN_PASSWORD`. That variable is needed only when creating
the first admin account.