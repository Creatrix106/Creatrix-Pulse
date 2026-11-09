class IngestionError(Exception):
    """A problem with the uploaded file that the user can fix. ``str(error)`` is shown verbatim in the UI
    (processing page and dataset card), so it must be a plain, actionable sentence."""
