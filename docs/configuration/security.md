# Security

## `ALLOWED_HOSTS`

_Default:_ `*` (any host)

Set this variable to a single host or comma-separated list of hosts.
This should _always_ be set to a specific host or hosts in production deployments.

Do not include schemes ("http" or "https") with this setting.

**Example value**

    baby.example.test, baby.example2.test

**See also**

- [Django's documentation on the ALLOWED_HOSTS setting](https://docs.djangoproject.com/en/5.0/ref/settings/#allowed-hosts)
- [`CSRF_TRUSTED_ORIGINS`](#csrf_trusted_origins)
- [`SECURE_PROXY_SSL_HEADER`](#secure_proxy_ssl_header)

## `API_THROTTLE_RATE_ANON`

_Default:_ `20/min`

Rate limit applied to unauthenticated requests to the REST API. django-axes only
protects the login form, so without a throttle the API can be probed without limit.

Set to an empty value to disable throttling of anonymous requests.

**Example value**

    5/min

## `API_THROTTLE_RATE_USER`

_Default:_ `1000/hour`

Rate limit applied to authenticated requests to the REST API. Set to an empty value to
disable throttling of authenticated requests.

**See also**

- [Django REST framework throttling documentation](https://www.django-rest-framework.org/api-guide/throttling/)

## `BABYBUDDY_ADMIN_PASSWORD`

_Default:_ `None` (a random password is generated)

Password for the initial superuser, which is created the first time migrations run and
only when no superuser exists yet.

If this is not set, a random password is generated and printed once to the output of the
`migrate` command. Anyone able to read those logs can use it, so log in and change the
password immediately.

**See also**

- [`BABYBUDDY_ADMIN_USERNAME`](#babybuddy_admin_username)

## `BABYBUDDY_ADMIN_USERNAME`

_Default:_ `admin`

Username for the initial superuser.

## `CORS_ALLOWED_ORIGINS`

_Default:_ `""` (no cross-origin requests allowed)

Set this variable to a single origin or comma-separated list of origins. Include schemes
("http" or "https") and any non-default ports in each origin.

This allows cross-origin requests to the API from the specified origins.

**Example value**

    https://other-domain.example.com, http://localhost:8888

**See also**

- [MDN article on CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [Making cross origin requests using fetch()](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch#making_cross-origin_requests)

## `CSRF_COOKIE_SECURE`

_Default:_ `False`

If this is set to `True`, the browser CSRF cookie will be marked as "secure", which instructs the browser to only send the cookie over an HTTPS connection (never HTTP).

**See also**

- [Django's documentation on the `CSRF_COOKIE_SECURE` setting](https://docs.djangoproject.com/en/5.0/ref/settings/#csrf-cookie-secure)

## `CSRF_TRUSTED_ORIGINS`

_Default:_ `None`

If Baby Buddy is behind a proxy, you may need add all possible origins to this setting
for form submission to work correctly. Separate multiple origins with commas.

Each entry must contain both the scheme (http, https) and fully-qualified domain name.

**Example value**

    https://baby.example.test,http://baby.example2.test,http://babybudy

**See also**

- [Django's documentation on the `CSRF_TRUSTED_ORIGINS` setting](https://docs.djangoproject.com/en/5.0/ref/settings/#std:setting-CSRF_TRUSTED_ORIGINS)
- [`ALLOWED_HOSTS`](#allowed_hosts)
- [`SECURE_PROXY_SSL_HEADER`](#secure_proxy_ssl_header)

## `PROXY_HEADER`

_Default:_ `HTTP_REMOTE_USER`

Sets the header to read the authenticated username from when
`REVERSE_PROXY_AUTH` has been enabled.

Baby Buddy modifies headers in the HTTP request; HTTP headers in the request have all characters converted to uppercase, replacing any hyphens with underscores and adding an HTTP\_ prefix to the name. For example `X-Auth-User` would be converted to `HTTP_X_AUTH_USER`.

**Example value**

    // For header key X-Auth-User
    HTTP_X_AUTH_USER

**See also**

- [Django's documentation on the `REMOTE_USER` authentication method](https://docs.djangoproject.com/en/5.0/howto/auth-remote-user/)
- [Django's documentation on the request.META object](https://docs.djangoproject.com/en/5.0/ref/request-response/#django.http.HttpRequest.META)
- [`REVERSE_PROXY_AUTH`](#reverse_proxy_auth)

## `REVERSE_PROXY_AUTH`

_Default:_ `False`

Enable use of `PROXY_HEADER` to pass the username of an authenticated user.
This setting should _only_ be used with a properly configured reverse proxy to
ensure the headers are not forwarded from sources other than your proxy.

**See also**

- [`PROXY_HEADER`](#proxy_header)

## `SECRET_KEY`

_Default:_ `None`

A random, unique string must be set as the "secret key" before Baby Buddy can
be deployed and run.

See also [Django's documentation on the SECRET_KEY setting](https://docs.djangoproject.com/en/5.0/ref/settings/#secret-key).

## `SECURE_PROXY_SSL_HEADER`

_Default:_ `None`

If Baby Buddy is behind a proxy, you may need to set this to `True` in order to
trust the `X-Forwarded-Proto` header that comes from your proxy, and any time
its value is "https". This guarantees the request is secure (i.e., it originally
came in via HTTPS).

**See also**

- [Django's documentation on the SECURE_PROXY_SSL_HEADER setting](https://docs.djangoproject.com/en/5.0/ref/settings/#secure-proxy-ssl-header)
- [`ALLOWED_HOSTS`](#allowed_hosts)
- [`CSRF_TRUSTED_ORIGINS`](#csrf_trusted_origins)

## `SECURE_HSTS_SECONDS`

_Default:_ `0` (disabled)

Number of seconds browsers should remember to reach the site over HTTPS only.

Browsers cache this value, so start with a small number (e.g. `300`) to confirm HTTPS
works before raising it to something like `31536000` (one year). Setting a large value
before TLS is working reliably makes the site unreachable over plain HTTP for that
duration.

**See also**

- [Django's documentation on HTTP Strict Transport Security](https://docs.djangoproject.com/en/5.0/ref/middleware/#http-strict-transport-security)
- [`SECURE_HSTS_INCLUDE_SUBDOMAINS`](#secure_hsts_include_subdomains)

## `SECURE_HSTS_INCLUDE_SUBDOMAINS`

_Default:_ `False`

Applies the HSTS policy to all subdomains. Only enable this if every subdomain is served
over HTTPS.

## `SECURE_HSTS_PRELOAD`

_Default:_ `False`

Adds the `preload` directive to the HSTS header, allowing the domain to be submitted to
browser preload lists. Requires `SECURE_HSTS_SECONDS` and
`SECURE_HSTS_INCLUDE_SUBDOMAINS`.

## `SECURE_SSL_REDIRECT`

_Default:_ `False`

Redirects all HTTP requests to HTTPS. Leave this disabled if the reverse proxy already
performs the redirect, which avoids a redundant round trip.

**See also**

- [Django's documentation on the `SECURE_SSL_REDIRECT` setting](https://docs.djangoproject.com/en/5.0/ref/settings/#secure-ssl-redirect)

## `SERVE_MEDIA_AUTHENTICATED`

_Default:_ `True`

Serves uploaded media - child pictures, note images and the thumbnails generated from
them - through a view that requires a logged in user.

Uploaded files keep their original names, so exposing the media directory directly from a
web server makes those files fetchable by anyone able to guess a name. Only disable this
if the proxy in front of Baby Buddy serves `MEDIA_URL` itself and applies its own access
control.

## `SESSION_COOKIE_AGE`

_Default:_ `1209600` (two weeks)

Lifetime of a login session in seconds. Sessions are refreshed while in use, so a long
value keeps a browser logged in more or less indefinitely.

**See also**

- [Django's documentation on the `SESSION_COOKIE_AGE` setting](https://docs.djangoproject.com/en/5.0/ref/settings/#session-cookie-age)

## `SESSION_COOKIE_SECURE`

_Default:_ `False`

If this is set to `True`, the browser session cookie will be marked as "secure", which instructs the browser to only send the cookie over an HTTPS connection (never HTTP).

**See also**

- [Django's documentation on the `SESSION_COOKIE_SECURE` setting](https://docs.djangoproject.com/en/5.0/ref/settings/#session-cookie-secure)
