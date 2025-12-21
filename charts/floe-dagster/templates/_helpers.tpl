{{/*
Helm template helpers for floe-dagster chart.

These templates provide common functions for:
- Generating consistent resource names
- Creating standard labels and selectors
- Building image references

Covers: 007-FR-001 (Helm chart for Kubernetes deployment)
*/}}

{{/*
Expand the name of the chart.
*/}}
{{- define "floe-dagster.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "floe-dagster.fullname" -}}
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
{{- define "floe-dagster.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels for all resources.
*/}}
{{- define "floe-dagster.labels" -}}
helm.sh/chart: {{ include "floe-dagster.chart" . }}
{{ include "floe-dagster.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: floe-runtime
{{- end }}

{{/*
Selector labels for pod matching.
*/}}
{{- define "floe-dagster.selectorLabels" -}}
app.kubernetes.io/name: {{ include "floe-dagster.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use.
*/}}
{{- define "floe-dagster.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "floe-dagster.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Generate image reference with tag defaulting to appVersion.
*/}}
{{- define "floe-dagster.image" -}}
{{- $tag := default .Chart.AppVersion .Values.image.tag }}
{{- printf "%s:%s" .Values.image.repository $tag }}
{{- end }}

{{/*
Generate the ConfigMap name for CompiledArtifacts.
*/}}
{{- define "floe-dagster.compiledArtifactsConfigMapName" -}}
{{- if .Values.floe.compiledArtifacts.configMapName }}
{{- .Values.floe.compiledArtifacts.configMapName }}
{{- else }}
{{- include "floe-dagster.fullname" . }}-compiled-artifacts
{{- end }}
{{- end }}
