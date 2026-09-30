# Pingram API Client

The Pingram API client provides email notification functionality for `solis_energy_manager`.

The module uses the [Pingram](https://www.pingram.io/) Python SDK to send HTML email notifications through the Pingram API. The API key and email addresses are supplied through the application `Settings` configuration.

## 1. Prerequisites

Before configuring the application, a Pingram account and API key are required.

The integration requires:

* A Pingram account
* A Pingram **secret API key**
* A destination email address
* Optionally, a CC email address

The Pingram API key is a secret and must not be committed to the repository or included directly in source code.

---

## 2. Create a Pingram Account

Create an account through the [Pingram website](https://www.pingram.io/).

Complete the initial account setup and sign in to the Pingram dashboard.

---

## 3. Create a Pingram API Key

Once signed in:

1. Open the **API Keys** section of the Pingram dashboard.
2. Create a new API key.
3. Create a **secret** API key for server-side API access.
4. Copy the secret immediately and store it securely.

Pingram only displays the complete secret key when it is created, so it should be saved securely at this point.

Secret API keys use the `pingram_sk_...` format.

For additional information, see the official Pingram [API key documentation](https://www.pingram.io/docs/api-reference/operations/keys_createapikey).

> **Important:** Never commit the Pingram API key to Git or store it directly in Python source code.

---

## 4. Configure the Application

The Pingram client obtains its configuration from the application's `Settings` object.

The following settings are required:

| Setting             | Description                                     |
| ------------------- | ----------------------------------------------- |
| `PINGRAM_API_KEY`   | Pingram secret API key                          |
| `DESTINATION_EMAIL` | Email address that should receive notifications |
| `CC_EMAIL`          | Email address to copy on notifications          |
| `FROM_NAME`         | Display name used for the sender                |

The Pingram API URL is also configurable through:

```text
PINGRAM_API_URL
```

The default value should point to the Pingram API endpoint appropriate for the account's region.

For example, the local `.env` file may contain:

```dotenv
PINGRAM_API_KEY=pingram_sk_...
DESTINATION_EMAIL=your-email@example.com
CC_EMAIL=your-email@example.com
FROM_NAME=Solis Energy Manager
```

The `.env` file should be excluded from version control.

If the project is deployed using a secrets manager or CI/CD environment variables, the same settings can be supplied through the deployment environment instead.

---

## 5. Module Implementation

The module exposes a single asynchronous function:

```python
async def send_email(
    settings: Settings,
    subject: str,
    html_content: str,
) -> None:
    """Send an email notification."""
```

The function accepts:

| Parameter      | Description                                                                     |
| -------------- | ------------------------------------------------------------------------------- |
| `settings`     | Application settings containing the Pingram credentials and email configuration |
| `subject`      | Subject of the email                                                            |
| `html_content` | HTML content of the email                                                       |

The function does not return a value.

### Example

```python
await send_email(
    settings=settings,
    subject="Battery status notification",
    html_content="<h1>Battery Status</h1><p>Battery state of charge: 85%</p>",
)
```

---

## 6. Pingram Client

The module creates a Pingram client using the configured API key and API URL:

```python
async with Pingram(
    api_key=settings.pingram_api_key.get_secret_value(),
    base_url=settings.pingram_api_url,
) as client:
```

The client is used as an asynchronous context manager. This ensures that the underlying client resources are properly opened and closed for each email request.

The API key is stored using Pydantic's `SecretStr` type in the application settings. `get_secret_value()` is used only when the key needs to be passed to the Pingram SDK.

---

## 7. Sending an Email

The module uses Pingram's `email_send` operation with a `SendEmailRequest`:

```python
await client.email.email_send(
    SendEmailRequest(
        type="email_compose_preview",
        to=settings.destination_email.get_secret_value(),
        ccAddresses=[settings.cc_email.get_secret_value()],
        subject=subject,
        html=html_content,
        fromName=settings.from_name,
        fromAddress="noreply@pingram.io",
    )
)
```

The request contains the following information:

| Field         | Description                   |
| ------------- | ----------------------------- |
| `type`        | Identifier for the email flow |
| `to`          | Primary recipient             |
| `ccAddresses` | CC recipients                 |
| `subject`     | Email subject                 |
| `html`        | HTML email body               |
| `fromName`    | Sender display name           |
| `fromAddress` | Sender email address          |

### Email Type

The `type` value identifies the email flow used by Pingram.

The current implementation uses:

```text
email_compose_preview
```

Pingram does not require the type to be separately created beforehand. The type is established/grouped when the email flow is used.

If the application introduces different notification categories, this value can be changed to a more application-specific identifier.

For example:

```text
solis_energy_manager_notification
```

or:

```text
battery_alert
```

The chosen value should remain consistent for the same type of notification.

---

## 8. Sender Address

The current implementation uses Pingram's default sender address:

```python
fromAddress = "noreply@pingram.io"
```

This avoids the need to configure a custom sending domain during initial setup.

A custom sender address can be used when a domain has been configured and verified with Pingram. This is an optional configuration and is not required for the basic integration.

See the Pingram [Email documentation](https://www.pingram.io/docs/email/overview) for information about sender and domain configuration.

---

## 9. HTML Email Content

The `html_content` argument is sent directly to Pingram as the HTML body of the email.

For example:

```python
html_content = """
<h1>Battery Status</h1>
<p>Current state of charge: <strong>85%</strong></p>
<p>The battery is currently charging.</p>
"""
```

This allows the application to generate formatted notifications containing information such as:

* Battery state of charge
* Battery charging/discharging status
* Solar generation
* Grid import/export
* Energy consumption
* Application errors or warnings

Keep generated HTML simple and self-contained to ensure that it renders consistently across email clients.

---

## 10. Security

The Pingram API key provides access to the Pingram API and must therefore be treated as a secret.

### Do

* Store the API key in an environment variable or secrets manager.
* Use `SecretStr` for the value in application settings.
* Keep `.env` files out of version control.
* Rotate the API key if it is accidentally exposed.

### Do not

* Commit the API key to Git.
* Put the API key directly in Python source code.
* Include the API key in application logs.
* Print the complete API key when troubleshooting.

The same principle applies to configured recipient addresses where they are considered sensitive configuration.

---

## 11. Troubleshooting

### Authentication errors

If Pingram rejects the request, check:

1. The API key is correct.
2. The API key has not been revoked.
3. The complete secret key was copied when it was created.
4. `PINGRAM_API_KEY` is available to the application.
5. The configured API URL corresponds to the Pingram account's region.

### Emails are not being received

Check:

1. `DESTINATION_EMAIL` contains the intended recipient.
2. `CC_EMAIL` is configured correctly.
3. The email has not been filtered into spam or junk.
4. The Pingram dashboard shows the request as successfully processed.
5. The HTML content is valid.

### API key is no longer available

Pingram does not display the complete secret API key again after creation. If the original key was not saved, create a new secret API key and update the application's configuration.

---

## 12. Official Pingram Documentation

The following Pingram documentation is useful when working with this integration:

* [Pingram Email Overview](https://www.pingram.io/docs/email/overview)
* [Pingram Send Emails Quick Start](https://www.pingram.io/docs/quick-start/send-emails)
* [Pingram API Key Reference](https://www.pingram.io/docs/api-reference/operations/keys_createapikey)

The module itself should remain deliberately small. Application-specific notification content and business logic should be handled by the calling code, while this module is responsible only for communicating with Pingram and sending the email.
