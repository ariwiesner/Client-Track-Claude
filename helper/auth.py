import tkinter as tk
from tkinter import messagebox

import keyring

from api_client import ApiClient, ApiError

SERVICE_NAME = 'ClientTracker'
KEYRING_USER = 'token'


def load_token():
    return keyring.get_password(SERVICE_NAME, KEYRING_USER)


def save_token(token):
    keyring.set_password(SERVICE_NAME, KEYRING_USER, token)


def clear_token():
    try:
        keyring.delete_password(SERVICE_NAME, KEYRING_USER)
    except keyring.errors.PasswordDeleteError:
        pass


def _prompt_login():
    """Blocking Tkinter login form. Returns a token string, or None if cancelled."""
    result = {'token': None}

    root = tk.Tk()
    root.title('Client Tracker — Log in')
    root.attributes('-topmost', True)
    root.resizable(False, False)

    tk.Label(root, text='Username').grid(row=0, column=0, padx=10, pady=(10, 4), sticky='w')
    username_entry = tk.Entry(root, width=28)
    username_entry.grid(row=0, column=1, padx=10, pady=(10, 4))
    username_entry.focus_set()

    tk.Label(root, text='Password').grid(row=1, column=0, padx=10, pady=4, sticky='w')
    password_entry = tk.Entry(root, width=28, show='*')
    password_entry.grid(row=1, column=1, padx=10, pady=4)

    error_label = tk.Label(root, text='', fg='red')
    error_label.grid(row=2, column=0, columnspan=2)

    def submit(event=None):
        username = username_entry.get().strip()
        password = password_entry.get()
        if not username or not password:
            return
        try:
            data = ApiClient().login(username, password)
            result['token'] = data['token']
            root.destroy()
        except ApiError as exc:
            error_label.config(text=str(exc))

    tk.Button(root, text='Log in', command=submit).grid(row=3, column=0, columnspan=2, pady=10)
    password_entry.bind('<Return>', submit)
    username_entry.bind('<Return>', lambda e: password_entry.focus_set())

    root.protocol('WM_DELETE_WINDOW', root.destroy)
    root.mainloop()
    return result['token']


def get_token(interactive=True):
    """Return a valid API token: cached one from keyring, or prompt to log in."""
    token = load_token()
    if token:
        client = ApiClient(token=token)
        try:
            client.me()
            return token
        except ApiError:
            clear_token()  # stale/invalid token

    if not interactive:
        return None

    token = _prompt_login()
    if token:
        save_token(token)
    return token
