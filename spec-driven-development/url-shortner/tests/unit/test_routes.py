import re

SEVEN_CHAR_SEGMENT = re.compile(r"^/[A-Za-z0-9]{7}$")


def route_paths(routes, prefix=""):
    """Flatten app routes; newer FastAPI keeps included routers as nested objects."""
    paths = []
    for route in routes:
        if hasattr(route, "original_router"):
            nested_prefix = prefix + route.include_context.prefix
            paths.extend(route_paths(route.original_router.routes, nested_prefix))
        else:
            paths.append(prefix + route.path)
    return paths


def test_no_app_page_can_be_shadowed_by_a_short_code(app):
    paths = route_paths(app.routes)

    assert "/{code}" in paths
    assert "/account/signin" in paths
    assert [path for path in paths if SEVEN_CHAR_SEGMENT.match(path)] == []


def test_short_link_route_is_registered_last(app):
    assert route_paths(app.routes)[-1] == "/{code}"
