subscribers = set()


def _normalize_name(name: str) -> str:
    cleaned_name = name.strip()
    if not cleaned_name:
        raise ValueError("empty name")
    return cleaned_name


def subscribe(name):
    cleaned_name = _normalize_name(name)
    subscribers.add(cleaned_name)
    return {"subscribed": True}


def unsubscribe(name):
    cleaned_name = _normalize_name(name)
    was_subscribed = cleaned_name in subscribers
    subscribers.discard(cleaned_name)
    return {"unsubscribed": was_subscribed}


def list_subscribers():
    return sorted(subscribers)
