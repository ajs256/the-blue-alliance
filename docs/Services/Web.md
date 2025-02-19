`web` is the service responsible for serving static content for The Blue Alliance. Although `web` handles the majority of responsibility in The Blue Alliance's stack, it's responsibilities should be limited to serving web pages and read-only actions. Create or update actions should be delegate to other services.

# Configuration

## Setup Javascript Secrets

Components in `web` (GameDay, login, etc.) make calls to Firebase and need to have Firebase keys set in order to work properly. Keys are referenced from a `tba_keys.js` file. This file is not checked in to source control, but an template of the file is. You can copy the template and add your own keys to the file.

```
$ cp src/backend/web/static/javascript/tba_js/tba_keys_template.js src/backend/web/static/javascript/tba_js/tba_keys.js
```

Edit the fields specified in the file and save. If you're using the development container, make sure to sync this file to the container. Finally, [rebuild web resources](https://github.com/the-blue-alliance/the-blue-alliance/wiki/Development-Runbook#rebuilding-web-resources-javascript-css-etc) to compile the secrets file with the Javascript.

## Rebuilding Web Resources (JavaScript, CSS, etc.)

If you make changes to JavaScript or CSS files for the `web` service, you will have to recompile the files in order for the changes to show up in your browser. After syncing changes from your local environment to the development container, run the `run_buildweb.sh` script from inside the development container.

```
$ ./ops/build/run_buildweb.sh
```

# Development

## Redirects

Redirecting to a page via the `next` URL parameter is a pattern used in The Blue Alliance codebase. Since this `next` parameter can be modified by a user, caution should be taken to ensure the `next` parameter is redirecting back to The Blue Alliance as expected before redirecting the user. [`redirect`](https://github.com/the-blue-alliance/the-blue-alliance/blob/py3/src/backend/web/redirect.py) offers some helpful commands for safely redirecting.

| Method | Description |
| --- | --- |
| `is_safe_url` | Given a URL, check that the URL redirects back to the current host and is a HTTP URL. |
| `safe_next_redirect` | Get a redirect Response from the `next` parameter. If the `next` parameter is not valid, the Response will be a redirect to the given fallback URL. |

```python
from backend.web.redirect import is_safe_url

def route() -> Response:
    next = request.args.get("next")
    # Make sure `next` is safe - otherwise drop it
    next = next if is_safe_url(next) else None
    return make_response(render_template(..., next=next))
```

```python
from backend.web.redirect import safe_next_redirect

def logout() -> Response:
    # Do some logout stuff here. Redirect to the `next` page. Fallback to the index page.
    return safe_next_redirect("/")
```

## Passing Data Between Pages

In some cases, data might want to be passed between pages. For example, a form flow with multiple steps or an action that has a failure state might want to use the state from the previous page when loading the next page. This data can be passed using the [Flask session](https://flask.palletsprojects.com/en/1.1.x/quickstart/#sessions). Session data is stored cryptographically in cookies and is safe to store secret or privileged information for a given user.

```python
from flask import request, session

def route() -> Response:
    if request.method == "POST":
        error = some_failable_work()
        if error:
            session["route_error"] = "work_failed"

        return redirect(url_for("route"))

    return make_response(
        render_template(
            ..., status=session.pop("route_error", None)
        )
    )
```

## Forms + POST

The `web` service uses [Flask WTF to enable CSRF protection](https://flask-wtf.readthedocs.io/en/stable/csrf.html). Since The Blue Alliance does not leverage `FlaskForm`, the CSRF token must be passed manually via the form. Form POSTs to the `web` service without a CSRF token will throw an exception.

```html
<form method="post">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
</form>
```

## Authentication + User

### Authentication Decorators

Use the [authentication decorators]((https://github.com/the-blue-alliance/the-blue-alliance/blob/py3/src/backend/web/decorators.py)) to ensure proper permission for a user for a given route.

| Method | Description |
| --- | --- |
| `require_login` | Ensures that a user is currently logged in and registered. If the user is not logged in, this method will automatically redirect the user to the login page and after logging in will redirect the user back to the original page. If the user is not registered, this method will automatically redirect the user to the registration page and after registering will redirect the user back to the original page. |
| `require_login_only` | Like `require_login` but does not require that a user is registered. |
| `enforce_login` | Ensures that a user is currently logged in - otherwise, this method will throw a 401. |
| `require_admin` | Ensures that a user is an admin. If the user is not logged in, this method will automatically redirect the user to the login page and after logging in will redirect the user back to the original page. |
| `require_permission` | Ensures that a user has a given permission. If the user is not logged in, this method will automatically redirect the user to the login page and after logging in will redirect the user back to the original page. If the user does not have the given permission, this method will throw a 401. |
| `require_any_permission` | Ensures that a user has any of the given permission. If the user is not logged in, this method will automatically redirect the user to the login page and after logging in will redirect the user back to the original page. If the user does not have any of the given permission, this method will throw a 401. |

```python
from backend.web.decorators import require_login

@require_login
def route() -> str:
    return render_template(...)
```

### Getting a User object

See the [[common|common]] page for details on how to obtain a user object through `current_user()`. The `User` object from `current_user()` is available in the HTML templates via the `user` property. If being used on a page that is not gated behind an authentication decorator, this property may be null. If the route is protected via the authentication decorators, the `current_user()` call can be wrapped in a `none_throws` call to ensure the object is not `None`.

```python
from pyre_extensions import none_throws

from backend.common.auth import current_user
from backend.web.decorators import require_login

@require_login
def route() -> str:
    user = none_throws(current_user())
    return render_template(..., api_read_keys=user.api_read_keys)
```

```html
{% if user %}
    <p>Welcome back, {{ user.display_name }}</p>
{% else %}
    <a href="login">Login</a>
{% endif }
```

### Safe User Actions

Requests that act on user data or on behalf of a user should be careful that the executing user has the proper permissions to perform the requested action. As previously mentioned, POST requests should pass a `csrf_token`. Required information should be fetched for only the currently logged in user. In some cases, a POST request might pass a user ID using the `user.uid` property in the template to ensure that the user is acting upon their own data when the request is made when relying on the currently logged in user is not enough validation (ex: editing account info).

Ex: Consider deleting an API key. A form might POST the API key to delete. The query to fetch the API key to delete should fetch the API key for the passed API key identifier **for the currently logged in user**. Failing to query the API key scoped to the given user would allow any user to delete any API key, regardless of if they're the owner of the API key.

The `User` model exposes several methods and properties that fetch data scoped for the user, and are considered safe. These methods should be preferred as opposed to writing custom queries or logic.

### Stubbing `current_user` + `User` in Tests

A [`login_user`](https://github.com/the-blue-alliance/the-blue-alliance/blob/py3/src/backend/web/handlers/conftest.py#L32) pytest fixture is available for stubbing the `current_user` function. `current_user` will return a `User` [Mock](https://docs.python.org/3/library/unittest.mock.html#unittest.mock.Mock) that can be used for verifying functionality.

```python
def test_register_account(login_user) -> None:
    login_user.is_registered = False

    with patch.object(login_user, "register") as mock_register:
        ...

    mock_register.assert_called_with("Zach")
```
