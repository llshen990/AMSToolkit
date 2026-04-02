class EscapeShellArg(object):
    @staticmethod
    def escape(arg):
        """
        Escape a string to be used as a shell argument
        Args:
            arg: str

        Returns: str
        """
        return "\\'".join("'" + p + "'" for p in arg.split("'"))
