=========
Changelog
=========

1.6.0 — UNRELEASED
==================

**Not released. ``bol/__init__.py`` still says 1.5.0 and no tag exists.** This
entry is prepared copy; cutting the release, bumping the version and creating
the tag are deliberate acts for the maintainer, because
``.github/workflows/python-publish.yml`` publishes to PyPI on every published
GitHub release and PyPI has no undo.

``RetailerAPI`` now accepts an optional ``transport=`` keyword, and the default
is unchanged: leave it out and the library builds the same ``requests.Session``
it always has, with the same headers, the same content-type on JSON bodies and
the same ``raise_for_status``. ``RetailerAPI(demo=True)`` followed by
``api.login(client_id, client_secret)`` works exactly as it did in 1.5.0, and
``api.session`` is still there. What is new is that you can now supply your own
HTTP implementation — anything with ``request``, ``login``, ``set_access_token``
and ``close``, documented as ``bol.retailer.transport.Transport`` — which makes
the library testable with no network and lets a caller add timeouts, retry,
rate limiting or logging without this package growing any of them. Two helpers
ship with it: ``build_uri``, the ``/{base}/{group}{path}`` rule the library
addresses bol.com with, and ``endpoint_group``, its inverse, which is what a
rate limiter needs in order to keep bol.com's per-group budgets apart instead of
merging them onto the segment ``retailer``.

**One deliberate behaviour change.** Argument guards that used to return
something unusable now raise ``ValueError`` naming the argument at fault.
``offers.updateProduct`` without ``fulfilment`` returned the *string*
``"{'error': 'Insufficient data provided'}"``, which is truthy, so an
``if response:`` check passed and the following line raised ``AttributeError``
somewhere unrelated; ``process_status.getByIds`` returned ``{}`` for a non-list;
``labels.getDeliveryOptions``, ``labels.createShippingLabel`` and the five
``insights`` methods returned ``None``. Nobody can have been relying on those
successfully.

Also fixed: ``transports.update`` built ``/retailer/{id}`` instead of
``/retailer/transports/{id}`` because the id was passed positionally into the
``override_group`` parameter; the login no longer sends the client secret in the
form body as well as the HTTP Basic header, which is the grant bol.com
documents; and three signatures no longer carry a mutable ``params={}``
default.

Known and unchanged: ``refresh_access_token`` remains broken. bol.com's
``client_credentials`` grant appears to issue no refresh token at all, so the
method posts a grant that is not offered and then reads a key that is not in
the reply. Whether the right answer is to fix it or to make it raise
``NotImplementedError`` depends on bol.com's own documentation and has not been
decided; it is left exactly as it was rather than changed on a guess.

Nothing was removed or renamed, and no argument became required.
