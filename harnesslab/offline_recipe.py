"""Render separate offline agent/verifier image targets, never execute builds."""
import re


def offline_recipe(base_reference):
    if not isinstance(base_reference,str) or not re.fullmatch(r'python@sha256:[a-f0-9]{64}',base_reference):
        raise ValueError('Expected observed immutable Python base digest')
    return f'''FROM {base_reference} AS agent
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
COPY agent-wheelhouse/ /opt/wheelhouse/
COPY agent.hashes.txt /opt/locks/runtime.txt
COPY agent-helper.hashes.txt /opt/locks/helper.txt
COPY agent-helper/ /opt/helper-wheelhouse/
RUN --network=none python3 -m venv /opt/agent && /opt/agent/bin/python -m pip install --no-index --find-links=/opt/wheelhouse --only-binary=:all: --require-hashes -r /opt/locks/runtime.txt && /opt/agent/bin/python -m pip install --no-index --no-deps --find-links=/opt/helper-wheelhouse --only-binary=:all: --require-hashes -r /opt/locks/helper.txt && /opt/agent/bin/python -m pip check
RUN --network=none git --version && /opt/agent/bin/python -I -c "import importlib.metadata as m; assert m.version('aider-chat')=='0.86.2'"
ENV PATH=/opt/agent/bin:/usr/local/bin:/usr/bin:/bin
WORKDIR /work
FROM {base_reference} AS verifier
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
COPY verifier-wheelhouse/ /opt/wheelhouse/
COPY verifier.hashes.txt /opt/locks/runtime.txt
COPY verifier-helper.hashes.txt /opt/locks/helper.txt
COPY verifier-helper/ /opt/helper-wheelhouse/
RUN --network=none python3 -m venv /opt/verifier && /opt/verifier/bin/python -m pip install --no-index --find-links=/opt/wheelhouse --only-binary=:all: --require-hashes -r /opt/locks/runtime.txt && /opt/verifier/bin/python -m pip install --no-index --no-deps --find-links=/opt/helper-wheelhouse --only-binary=:all: --require-hashes -r /opt/locks/helper.txt && /opt/verifier/bin/python -m pip check
RUN --network=none /opt/verifier/bin/python -I -c "import importlib.metadata as m; assert m.version('pytest')=='8.3.5'"
ENV PATH=/opt/verifier/bin:/usr/local/bin:/usr/bin:/bin
WORKDIR /work
'''
