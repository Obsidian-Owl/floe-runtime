{{/*
Expand the name of the chart.
*/}}
{{- define "floe-infrastructure.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "floe-infrastructure.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "floe-infrastructure.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "floe-infrastructure.labels" -}}
helm.sh/chart: {{ include "floe-infrastructure.chart" . }}
{{ include "floe-infrastructure.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "floe-infrastructure.selectorLabels" -}}
app.kubernetes.io/name: {{ include "floe-infrastructure.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "floe-infrastructure.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "floe-infrastructure.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
PostgreSQL host
*/}}
{{- define "floe-infrastructure.postgresql.host" -}}
{{- printf "%s-postgresql" .Release.Name }}
{{- end }}

{{/*
PostgreSQL port
*/}}
{{- define "floe-infrastructure.postgresql.port" -}}
{{- print "5432" }}
{{- end }}

{{/*
MinIO endpoint (legacy - use storage.endpoint instead)
*/}}
{{- define "floe-infrastructure.minio.endpoint" -}}
{{- printf "http://%s-minio:9000" .Release.Name }}
{{- end }}

{{/*
Storage endpoint - cloud-agnostic (supports LocalStack, MinIO, ADLS, GCS)
Returns the appropriate endpoint based on enabled storage provider.
*/}}
{{- define "floe-infrastructure.storage.endpoint" -}}
{{- if .Values.localstack.enabled }}
{{- printf "http://%s-localstack:4566" .Release.Name }}
{{- else if .Values.minio.enabled }}
{{- printf "http://%s-minio:9000" .Release.Name }}
{{- else if .Values.azurite.enabled }}
{{- printf "http://%s-azurite:10000" .Release.Name }}
{{- else }}
{{- printf "http://%s-localstack:4566" .Release.Name }}
{{- end }}
{{- end }}

{{/*
Polaris endpoint
*/}}
{{- define "floe-infrastructure.polaris.endpoint" -}}
{{- printf "http://%s-polaris:8181" .Release.Name }}
{{- end }}

{{/*
Jaeger UI endpoint (query service)
*/}}
{{- define "floe-infrastructure.jaeger.endpoint" -}}
{{- printf "http://%s-jaeger:16686" .Release.Name }}
{{- end }}

{{/*
Jaeger OTLP endpoint (collector service for traces)
The Jaeger Helm chart creates separate services:
- <release>-jaeger (query, port 16686)
- <release>-jaeger-collector (OTLP gRPC, port 4317)
*/}}
{{- define "floe-infrastructure.jaeger.otlp.endpoint" -}}
{{- printf "http://%s-jaeger-collector:4317" .Release.Name }}
{{- end }}

{{/*
Marquez endpoint
*/}}
{{- define "floe-infrastructure.marquez.endpoint" -}}
{{- printf "http://%s-marquez:5000" .Release.Name }}
{{- end }}

{{/*
LocalStack endpoint
*/}}
{{- define "floe-infrastructure.localstack.endpoint" -}}
{{- printf "http://%s-localstack:4566" .Release.Name }}
{{- end }}

{{/*
S3 endpoint - legacy alias for storage.endpoint (use storage.endpoint for cloud-agnostic code)
*/}}
{{- define "floe-infrastructure.s3.endpoint" -}}
{{- include "floe-infrastructure.storage.endpoint" . }}
{{- end }}

{{/*
Polaris catalog name
*/}}
{{- define "floe-infrastructure.polaris.catalogName" -}}
{{- default "demo_catalog" .Values.polarisInit.catalogName }}
{{- end }}
