"""
Provides supplementary functionality to simplify the coordination of tools'
user interfaces with separate state objects.
"""

class CallbackNotifier(object):
    """
    Base class for an object that supports a number of events, allowing
    callbacks to be registered with those events. Callbacks are executed when
    the implementing class executes the _notify method.
    """
    def __init__(self, supported_events):
        """
        Initializes a new callback notifier that supports the given list of
        string event names.
        """
        self.__callbacks = {} # str -> [callable]
        self.__supported_events = supported_events

    def register(self, event_name, *callbacks):
        """
        Adds the ordered list of callback functions to the list of callbacks
        registered with the given event. Any callbacks that are already
        registered will simply be ignored.
        """
        self.__check_support(event_name)

        if event_name not in self.__callbacks:
            self.__callbacks[event_name] = []

        for callback in callbacks:
            if callback not in self.__callbacks[event_name]:
                self.__callbacks[event_name].append(callback)

    def unregister(self, event_name, *callbacks):
        """
        Removes the specified callback functions from the list of callbacks
        registered with the given event. Any callbacks not already registered
        will simply be ignored.
        """
        self.__check_support(event_name)

        if event_name not in self.__callbacks:
            return

        for callback in callbacks:
            if callback in self.__callbacks[event_name]:
                self.__callbacks[event_name].remove(callback)

    def _notify(self, event_name):
        """
        Executes all the callbacks registered with the given event.
        """
        self.__check_support(event_name)

        if event_name not in self.__callbacks:
            return

        for callback in self.__callbacks[event_name]:
            callback()

    def __check_support(self, event_name):
        """
        Checks the list of supported events to ensure that the event with the
        given name is indeed supported by this class. Raises a TypeError if the
        event is unsupported; otherwise passes without effect.
        """
        if not event_name in self.__supported_events:
            raise TypeError('%s does not support an event named "%s"!' % (
                self.__class__.__name__, event_name
            ))
