## Settings Configuration

*Django RecomPI* can be customized through the following settings in your `settings.py` file:

### `RECOMPI_API_KEY`

- **Type:** `str`
- **Description:** API key for accessing the RecomPI service. Required for integration.
- **Note:** To obtain `RECOMPI_API_KEY`, register on the [RecomPI panel](https://panel.recompi.com/clients/sign_in). After registration, [add a campaign](https://panel.recompi.com/campaigns/new) in the panel, and a campaign token will be generated instantly. Use this token as your API key in the code.

### `RECOMPI_SECURE_API`

- **Type:** `bool`
- **Default:** `True`
- **Description:** Flag indicating whether to use secure API connections.

### `RECOMPI_SECURE_HASH_SALT`

- **Type:** `str` or `None`
- **Description:** Salt used to hash profile information securely. Profiles hashed with this salt before sending data to RecomPI servers using `SecureProfile`.