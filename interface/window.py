"""
Provides functionality for creating and working with tool windows in Maya.
"""

import maya.cmds as mc

class Window(object):
    """
    Represents the window for a GUI-based tool, created with Maya's window
    command. This class encapsulates the boilerplate code necessary to create
    and configure a window in Maya.
    """
    def __init__(self, name, title, size, flags = None,
                                          remember_size = (True, False)):
        """
        Creates a new window with the given parameters. GUI controls created
        subsequently will be a part of the new window. Once configured, the
        window may be opened with the show method.

        @param name: The internal name used to uniquely identify the window in
            Maya.
        @param title: The user-facing name to be displayed in the window's
            titlebar.
        @param size: A pair representing the initial width and height of the
            window.
        @param flags: A dictionary containing any additional flags to be passed
            to the window command.
        @param remember_size: A pair representing whether the width and height
            of the window should be remembered after it's closed. A value of
            False for either dimension indicates that the stored width or
            height value should be reset to the initial value each time the
            window is opened.
        """
        self.name = name

        # Delete the window if it already exists
        if mc.window(self.name, query = True, exists = True):
            mc.deleteUI(self.name)

        # Reset the window settings to discard stored width and/or height
        width, height = size
        remember_width, remember_height = remember_size
        if mc.windowPref(self.name, exists = True):
            get_pref = lambda attr: mc.windowPref(self.name,
                                                  **{'query': True, attr: True})
            mc.windowPref(self.name,
                leftEdge = get_pref('leftEdge'),
                topEdge = get_pref('topEdge'),
                width = get_pref('width') if remember_width else width,
                height = get_pref('height') if remember_height else height)

        # Prepare the flags to use in creating the window
        flags = flags or {}
        flags['title'] = title
        flags['width'] = width
        flags['height'] = height

        # Make these flags True if not provided, overriding the Maya default
        for key in ['toolbox', 'resizeToFitChildren']:
            if key not in flags:
                flags[key] = True

        # Create the window
        mc.window(self.name, **flags)

    def attach_callback(self, event_name, callback):
        """
        Uses a script job to attach a callback to the window. When the given
        event is fired, the callback will be executed. The script job
        associated with the callback will be automatically killed when the
        window is deleted.
        """
        job = mc.scriptJob(event = [event_name, callback])
        detach_callback = lambda: mc.scriptJob(kill = job, force = True)
        mc.scriptJob(uiDeleted = [self.name, detach_callback])

    def show(self):
        """
        Opens the window.
        """
        mc.showWindow(self.name)
