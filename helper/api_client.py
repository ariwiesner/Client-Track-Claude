import requests

import config


class ApiError(Exception):
    pass


class ApiClient:
    def __init__(self, token=None):
        self.token = token

    def _headers(self):
        headers = {}
        if self.token:
            headers['Authorization'] = f'Token {self.token}'
        return headers

    def _request(self, method, path, **kwargs):
        url = f'{config.API_URL}{path}'
        try:
            resp = requests.request(
                method, url, headers=self._headers(), verify=config.CA_BUNDLE, timeout=10, **kwargs
            )
        except requests.RequestException as exc:
            raise ApiError(str(exc)) from exc

        if resp.status_code == 204:
            return None
        if not resp.ok:
            detail = resp.text
            try:
                detail = resp.json().get('detail', detail)
            except ValueError:
                pass
            raise ApiError(f'{resp.status_code}: {detail}')
        if not resp.content:
            return None
        return resp.json()

    def login(self, username, password):
        return self._request('POST', '/auth/login/', json={'username': username, 'password': password})

    def me(self):
        return self._request('GET', '/auth/me/')

    def list_clients(self):
        return self._request('GET', '/clients/')

    def list_systems(self):
        return self._request('GET', '/systems/')

    def current_time_entry(self):
        return self._request('GET', '/time-entries/current/')

    def start_time_entry(self, client_id, source='auto', system_id=None):
        return self._request(
            'POST', '/time-entries/start/',
            json={'client_id': client_id, 'source': source, 'system_id': system_id},
        )

    def stop_time_entry(self, entry_id):
        return self._request('POST', f'/time-entries/{entry_id}/stop/')

    def cancel_time_entry(self, entry_id):
        return self._request('POST', f'/time-entries/{entry_id}/cancel/')

    def resume_time_entry(self, entry_id):
        return self._request('POST', f'/time-entries/{entry_id}/resume/')
