subscribers = set()


def subscribe(name):
    if not name.strip():
        raise ValueError("empty name")
    subscribers.add(name.strip())
    return {"subscribed": True}


def unsubscribe(name):
    cleaned_name = name.strip()
    if not cleaned_name:
        raise ValueError("empty name")
    was_subscribed = cleaned_name in subscribers
    subscribers.discard(cleaned_name)
    return {"unsubscribed": was_subscribed}


def list_subscribers():
    return sorted(subscribers)
