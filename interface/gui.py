"""
Provides functionality related to Maya GUI controls.
"""

import re

import maya.cmds as mc
import maya.mel as mel

class Control(object):
    """
    Represents a single UI control contained within a Gui. Provides a wrapper
    for the MEL command associated with whatever control type, including
    methods to edit and query the parameters of the control.
    """
    def __init__(self, name, control_type, creation_flags, parent_name):
        """
        Initializes a new control declaration with the given name and control
        type. creation_flags is a string containing the MEL flags and arguments
        used to create the control (excluding the command, the name, and the
        -p[arent] flag). parent_name is the name of this control's parent, or
        None if no parent is specified.
        """
        self.name = name
        self.control_type = control_type
        self.creation_flags = creation_flags
        self.parent_name = parent_name

    def delete(self):
        """
        Deletes this control and all of its children.
        """
        mc.deleteUI(self.name)

    def create(self):
        """
        Executes the MEL command that creates this control based on its
        creation parameters.
        """
        # Construct the MEL command to create this control based on its
        # parameters
        parent_flag = (' -p %s' % self.parent_name) if self.parent_name else ''
        command = '%s%s %s %s;' % (
            self.control_type,
            parent_flag,
            self.creation_flags,
            self.name)

        # Attempt to execute the command as MEL. If unsuccessful, print the
        # full command so we can diagnose the problem.
        try:
            mel.eval(command)
        except RuntimeError, exc:
            print '// %s //' % command
            raise exc

    def edit(self, **flags):
        """
        Edits this control with the given new flag values. The provided
        dictionary of flags need not contain the edit flag.
        """
        def thunk_commands(flags):
            """
            Modifies and returns the given dictionary so that all function
            values associated with command flags are thunked into anonymous
            functions that ignore the arguments passed to them by Maya. 
            """
            for flag, value in flags.iteritems():
                if 'command' in flag.lower() and hasattr(value, '__call__'):
                    flags[flag] = lambda _: value()
            return flags

        flags['edit'] = True
        self._call_command(thunk_commands(flags))

    def query(self, flag):
        """
        Returns the current value of the specified flag.
        """
        return self._call_command({'query': True, flag: True})

    def _call_command(self, flags):
        """
        Private helper method that calls the MEL command associated with the
        relevant type of control, passing in this control's name and the given
        set of flag mappings.
        """
        command = mc.__dict__[self.control_type]
        return command(self.name, **flags)

    @classmethod
    def from_string(cls, name, command, parent_name):
        """
        Instantiates a new Control object from the provided pieces of its
        string declaration.
        """
        # Capture an explicitly specified parent name in the declaration
        parent_name_regex = re.search(r' -p(?:arent)? "?([A-Za-z0-9_]+)"? ?',
                                      command)

        # If a parent name has been specified, extract it from the command
        if parent_name_regex:
            parent_name = parent_name_regex.group(1)
            command = command.replace(parent_name_regex.group(0), ' ')

        # Split the MEL command used to create the control: the first word is
        # the control type, and everything after that represents flags
        command_tokens = command.split()
        control_type = command_tokens[0]
        creation_flags = ' '.join(command_tokens[1:])

        # Instantiate a new control declaration from these parameters
        return cls(name, control_type, creation_flags, parent_name)

class Gui(object):
    """
    Represents a set of controls created from a string declaration via the
    from_string classmethod. Once a Gui is created (by calling the create
    method after a window has been created), individual controls from the
    declaration can be accessed with square-bracket notation to be manipulated
    individually. In addition, the edit method can be used to process a batch
    of edits in a single call.
    """
    def __init__(self, controls):
        """
        Initializes a new Gui from the given list of Control objects.
        """        
        self._controls = []
        self._control_lookup = {}
        
        for control in controls:
            self.add(control)

    def __getitem__(self, key):
        """
        Allows individual controls to be accessed by name using array-style
        indexing into the Gui object.
        """
        return self._control_lookup[key]

    def add(self, control):
        """
        Adds the specified control object to the Gui.
        """
        self._controls.append(control)
        self._control_lookup[control.name] = control

    def create(self):
        """
        Creates the Gui by creating all of its controls. 
        """
        for control in self._controls:
            control.create()

    def extend(self, other):
        """
        Extends this Gui by adding and creating the controls contained in
        another Gui object.
        """
        for control in other._controls:
            self.add(control)
        other.create()

    def edit(self, per_control_edits):
        """
        Processes an unordered batch of edits for a subset of this Gui's
        controls. per_control_edits is a dictionary mapping each control name
        with a dictionary containing the flags and values specifying the edits
        to be made to that control.
        """
        for control_name, edit_flags in per_control_edits.iteritems():
            self[control_name].edit(**edit_flags)

    @classmethod
    def from_string(cls, s):
        """
        Instantiates a new Gui object from a string declaration.
        """
        def strip_comments(line):
            """
            Given a line, returns the same line with any comments stripped away.
            Comments begin with a hash character ("#") and continue to the end
            of the line thereafter.
            """
            # Establish some local state to use in scanning the string.
            # quote_open indicates whether the characters over which we're
            # currently iterating are contained within a quoted span, and
            # quote_chars contains the set of characters currently considered
            # valid opening or closing characters for a quoted span.
            quote_open = False
            quote_chars = ['"', "'"]

            def open_quote(quote_char):
                """
                Modifies local state to indicate that we're scanning over a
                region of the string that's enclosed in quotes. quote_char is
                the character that opens the quote. 
                """
                quote_open = True
                quote_chars = [quote_char]

            def close_quote():
                """
                Modifies local state to indicate that we're no longer scanning
                over a quoted region of the string.
                """
                quote_open = False
                quote_chars = ['"', "'"]

            # Iterate over each character in the string. If we encounter an
            # unquoted hash character, we can immediately strip it away and
            # return the part of the string before it. Otherwise, we keep
            # iterating, checking each character to determine if we need to
            # open or close a quote.
            for i, c in enumerate(line):
                if c == '#' and not quote_open:
                    return line[:i]
                elif c in quote_chars:
                    close_quote() if quote_open else open_quote(c)

            # Return the entire line unmodified if we encounter no hashes.
            return line

        def parse_line(lines):
            """
            Parses the given line, returning a triple containing the line's
            indentation level, the name of the control declared on that line,
            and the creation command associated with that control.
            """
            def get_indentation_level(line):
                """
                Returns the number of spaces at the beginning of the line.
                Treats each tab character as four spaces.
                """
                match = re.match(r'[ \t]*', line)
                if not match:
                    return 0
                return len(match.group(0).replace('\t', '    '))

            def split_control(line):
                """
                Splits the given line at the first colon, returning the pair of
                the control name and the creation command associated with that
                control.
                """
                first_colon_index = line.find(':')
                return (line[:first_colon_index].strip(),
                        line[first_colon_index+1:].strip())

            declaration_triples = []
            
            for line in lines:
                indentation_level = get_indentation_level(line)
                name, command = split_control(line)
                declaration_triples.append((indentation_level, name, command))

            return declaration_triples

        class ControlStack(object):
            """
            Data structure used to keep track of the controls encountered when
            parsing the input string.
            """
            def __init__(self):
                """
                Initializes an empty control stack.
                """
                self._controls = [(-1, None)]

            def pop(self, indentation_level):
                """
                Pops controls off the top of the stack until the topmost
                control is below the given indentation level.
                """
                while self._controls[-1][0] >= indentation_level:
                    self._controls.pop()

            def push(self, indentation_level, control_name):
                """
                Pushes a new control onto the stack at the given indentation
                level.
                """
                assert indentation_level > self._controls[-1][0]
                self._controls.append((indentation_level, control_name))

            @property
            def top_control(self):
                """
                Returns the topmost control name on the stack.
                """
                return self._controls[-1][1]

        # Strip comments and blank lines to give us only the meaningful lines
        commentless_lines = [strip_comments(line) for line in s.splitlines()]
        meaningful_lines = [line for line in commentless_lines if line.strip()]
        
        # Iterate over each line to collect control declarations, using a stack
        # to infer parent controls based on indentation
        controls = []
        control_stack = ControlStack()

        for (indentation_level,
             control_name,
             control_command) in parse_line(meaningful_lines):

            # Slice off the top of the stack so that we're back to the last-seen
            # control that's below the indentation level of the current one
            control_stack.pop(indentation_level)

            # Create a new control declaration, using the new top of the stack
            # as its parent control
            controls.append(Control.from_string(control_name,
                                                control_command,
                                                control_stack.top_control))

            # Push the current control onto the stack, as it's now the last-seen
            # control of its indentation level
            control_stack.push(indentation_level, control_name)

        # Instantiate and return a new Gui object from the parsed controls
        return cls(controls)
