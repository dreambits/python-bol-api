"""The HTTP seam of :class:`bol.retailer.api.RetailerAPI`.

``RetailerAPI`` used to own a :class:`requests.Session` and drive it directly.
Everything it does over the wire now goes through a *transport*, which is any
object with the four methods :class:`Transport` documents. The default,
:class:`RequestsTransport`, is the old behaviour moved here unchanged, so
nothing about the library's out-of-the-box behaviour differs.

The point of the seam is that a caller who needs timeouts, bounded retry,
throttling, typed errors or redacted logging can supply their own transport
without this library having to grow — or depend on — any of it. Nothing in this
module imports anything beyond the standard library and ``requests``.

Two module-level helpers also live here because they are the *same* piece of
knowledge used from two directions:

* :func:`build_uri` is the ``/{base}/{group}{path}`` rule, and
  :meth:`bol.retailer.api.MethodGroup.request` calls it rather than repeating
  it;
* :func:`endpoint_group` reads that rule backwards, turning a URL or path back
  into the resource group it addresses. A caller that rate-limits per endpoint
  group needs exactly this, and getting it wrong is silent: bol.com's budgets
  differ per group (25 for orders, 20 for returns, 100 for economic-operators),
  so grouping ``/retailer/orders`` and ``/retailer/economic-operators`` together
  makes a limiter believe it has budget it does not have.
"""

try:
    from urllib.parse import urlsplit
except ImportError:  # Python 2
    from urlparse import urlsplit

import requests

__all__ = [
    "Transport",
    "RequestsTransport",
    "build_uri",
    "endpoint_group",
    "BASE_TYPES",
    "DEMO_SUFFIX",
    "JSON_CONTENT_TYPE",
    "DEFAULT_ACCEPT",
    "RETAILER_ACCEPT",
]

#: Sent as ``content-type`` whenever a request carries a JSON body. Without it
#: the API answers 400.
#: https://api.bol.com/retailer/public/conventions/index.html
JSON_CONTENT_TYPE = "application/vnd.retailer.v10+json"

#: Pinned on the session at construction, as it always has been.
DEFAULT_ACCEPT = "application/json"

#: Pinned on the session once a token is set.
RETAILER_ACCEPT = "application/vnd.retailer.v10+json"

#: The ``base`` half of ``/{base}/{group}``. ``retailer`` is
#: :class:`~bol.retailer.api.MethodGroup`'s default; ``shared`` is what
#: process-status passes. :func:`endpoint_group` needs to recognise them to
#: know that the *second* segment is the group.
BASE_TYPES = frozenset(["retailer", "shared"])

#: Appended to the base type when the API is used in demo mode.
DEMO_SUFFIX = "-demo"

# Distinguishes "no json body" from "a json body that happens to be None".
# Only the former may skip the content-type header, which is how the library
# has always behaved.
_UNSET = object()


def build_uri(base_type, group, path="", demo=False):
    """Build the request URI for one method group call.

    This is the single definition of bol.com's ``/{base}/{group}{path}``
    convention. :meth:`bol.retailer.api.MethodGroup.request` calls it, and
    :func:`endpoint_group` is its inverse.
    """
    return "/{base}/{group}{path}".format(
        base=(base_type + DEMO_SUFFIX) if demo else base_type,
        group=group,
        path=("/{}".format(path) if path else ""),
    )


def endpoint_group(url_or_path):
    """The resource group a URL or path addresses — the inverse of :func:`build_uri`.

    ``/retailer/orders/123`` and ``https://api.bol.com/retailer-demo/orders``
    are both ``orders``; ``/shared/process-status`` is ``process-status``. A
    path that does not start with a known base type falls back to its first
    segment, so a caller whose base URL already carries the prefix and asks for
    ``/orders`` gets the same answer.

    This exists because bol.com publishes a *different* rate-limit budget per
    group. Grouping on the first path segment — the obvious thing, and the
    default of most limiters — collapses ``orders``, ``offers``, ``returns``
    and ``economic-operators`` onto ``retailer``, which is wrong in the
    dangerous direction: the largest budget seen overwrites the smallest.
    """
    path = urlsplit(str(url_or_path or "")).path
    segments = [segment for segment in path.split("/") if segment]
    if not segments:
        return ""
    if _is_base_type(segments[0]) and len(segments) > 1:
        return segments[1]
    return segments[0]


def _is_base_type(segment):
    if segment.endswith(DEMO_SUFFIX):
        segment = segment[: -len(DEMO_SUFFIX)]
    return segment in BASE_TYPES


class Transport(object):
    """What :class:`~bol.retailer.api.RetailerAPI` needs from whatever performs its HTTP.

    Implementations do **not** have to subclass this — ``RetailerAPI`` only
    calls the four methods and never type-checks. Subclass it if inheriting the
    docstrings is useful; duck-type it otherwise. It is written down because it
    is now a public extension point of this library.
    """

    def request(self, method, url, params=None, json=_UNSET, headers=None,
                timeout=None, **kwargs):
        """Perform one API call and return a :class:`requests.Response`.

        ``RetailerAPI`` passes everything except ``method`` and ``url`` by
        keyword, so an implementation is free to make them keyword-only.

        ``url`` is absolute. ``timeout`` of ``None`` means "use whatever
        default the transport was configured with"; it does not mean "no
        timeout" unless that default is itself ``None``.

        Must **return the response**, not a parsed body: five of this library's
        methods hand the response straight back to the caller so it can read
        CSV or PDF bytes.

        Must raise on an error status. :class:`RequestsTransport` raises
        :class:`requests.HTTPError` via ``raise_for_status``; a transport with
        its own exception hierarchy may raise that instead.
        """
        raise NotImplementedError

    def login(self, login_url, client_id, client_secret):
        """Obtain a token and return the parsed token document.

        The returned mapping must contain ``access_token``;
        :meth:`~bol.retailer.api.RetailerAPI.login` returns it to the caller
        unchanged. A transport that manages its own credentials should still
        return a mapping of that shape, or raise, rather than quietly doing
        nothing — a silent no-op here looks exactly like a successful login.
        """
        raise NotImplementedError

    def set_access_token(self, access_token):
        """Use ``access_token`` for subsequent requests."""
        raise NotImplementedError

    def close(self):
        """Release any underlying connection resources."""
        raise NotImplementedError


class RequestsTransport(Transport):
    """The default transport: a :class:`requests.Session`, driven as before.

    This class exists to guarantee that adding the seam changed nothing. Every
    line of it was moved out of ``RetailerAPI`` — the session, the ``Accept``
    header pinned at construction, the content-type injected when there is a
    JSON body, the ``raise_for_status``. If you are tempted to improve
    something here, remember that every public user of this package gets that
    improvement whether they asked for it or not.
    """

    def __init__(self, session=None, timeout=None):
        self.session = session or requests.Session()
        self.session.headers.update({"Accept": DEFAULT_ACCEPT})
        self.timeout = timeout

    def request(self, method, url, params=None, json=_UNSET, headers=None,
                timeout=None, **kwargs):
        request_kwargs = dict(kwargs)
        if json is not _UNSET:
            request_kwargs["json"] = json
        if headers is not None:
            # Copied, not aliased: the content-type below would otherwise be
            # written into the caller's own dict.
            request_kwargs["headers"] = dict(headers)
        request_kwargs.update(
            {
                "method": method,
                "url": url,
                "params": {} if params is None else params,
                "timeout": self.timeout if timeout is None else timeout,
            }
        )
        if "json" in request_kwargs:
            if "headers" not in request_kwargs:
                request_kwargs["headers"] = {}
            # If these headers are not added, the api returns a 400
            # Reference:
            #   https://api.bol.com/retailer/public/conventions/index.html
            request_kwargs["headers"].update({"content-type": JSON_CONTENT_TYPE})

        resp = self.session.request(**request_kwargs)
        resp.raise_for_status()
        return resp

    def login(self, login_url, client_id, client_secret):
        # The credentials go in the Basic header only. bol.com's documented
        # client_credentials grant is HTTP Basic, and a copy in the form body
        # is one more place the secret can be logged by a proxy or a debug hook
        # that knows to redact Authorization and nothing else.
        resp = self.session.post(
            login_url + "/token",
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials"},
        )
        resp.raise_for_status()
        return resp.json()

    def set_access_token(self, access_token):
        self.session.headers.update(
            {
                "Authorization": "Bearer " + access_token,
                "Accept": RETAILER_ACCEPT,
            }
        )

    def close(self):
        self.session.close()
