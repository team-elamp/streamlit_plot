FROM semgrep/semgrep:1.187.0@sha256:4150825595755b157d47ddd05d263814b5429617336faa645f3ad15892ca946d
ADD --checksum=sha256:c7cbe3137fb8a48a17574bede3dd6beb16742d1e9772929940fc90082c39d9c0 https://github.com/aquasecurity/trivy/releases/download/v0.76.1/trivy_0.76.1_Linux-64bit.tar.gz /tmp/trivy.tar.gz
RUN tar -xzf /tmp/trivy.tar.gz -C /usr/local/bin trivy && rm /tmp/trivy.tar.gz
COPY scan.py rules.yml /opt/elamp-security/
RUN printf '{}\n' > /opt/elamp-security/empty.yaml
ENV SEMGREP_SEND_METRICS=off SEMGREP_ENABLE_VERSION_CHECK=0 TRIVY_DISABLE_TELEMETRY=true
LABEL dev.workspace.lifecycle=temporary dev.workspace.task=elamp-security-ci-20261126
ENTRYPOINT ["python3", "/opt/elamp-security/scan.py"]
