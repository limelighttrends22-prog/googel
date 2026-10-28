"""Local convenience tasks; release validation uses pytest and build."""
import nox


@nox.session(python='3.12')
def tests(session):
    session.install('-r','requirements-dev.lock.txt')
    session.install('--no-deps','-e','.')
    session.run('python','-m','pytest','-ra')


@nox.session(venv_backend='none')
def lint(session):
    session.run('black','--check','-l','80','ads_mcp','tests')


@nox.session(venv_backend='none')
def format(session):
    session.run('black','-l','80','ads_mcp','tests')
