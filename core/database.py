def conflito_transitorio(error):
    """SQLSTATE de serialização, deadlock ou indisponibilidade de bloqueio."""
    cause = error.__cause__
    return getattr(cause, 'sqlstate', None) in {'40001', '40P01', '55P03'}
