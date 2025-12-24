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

{{/*
Generate the ConfigMap name for Platform configuration.
Supports both internal (platformSpec) and external (externalPlatformConfig) modes.
Two-Tier Architecture: Platform.yaml drives K8s configuration.
*/}}
{{- define "floe-dagster.platformConfigMapName" -}}
{{- if .Values.floe.externalPlatformConfig.enabled }}
{{- required "externalPlatformConfig.configMapName is required when externalPlatformConfig.enabled=true" .Values.floe.externalPlatformConfig.configMapName }}
{{- else if .Values.floe.platformSpec.enabled }}
{{- include "floe-dagster.fullname" . }}-platform
{{- end }}
{{- end }}

{{/*
Generate volume configuration for platform ConfigMap mount.
Two-Tier Architecture: Mounts platform.yaml for PlatformResolver to load.
*/}}
{{- define "floe-dagster.platformConfigVolume" -}}
{{- if or .Values.floe.platformSpec.enabled .Values.floe.externalPlatformConfig.enabled }}
- name: platform-config
  configMap:
    name: {{ include "floe-dagster.platformConfigMapName" . }}
    items:
      - key: {{ .Values.floe.externalPlatformConfig.configMapKey | default "platform.yaml" }}
        path: platform.yaml
{{- end }}
{{- end }}

{{/*
Generate volumeMount configuration for platform ConfigMap.
Two-Tier Architecture: Mounts platform.yaml at standard location.
*/}}
{{- define "floe-dagster.platformConfigVolumeMount" -}}
{{- if .Values.floe.externalPlatformConfig.enabled }}
- name: platform-config
  mountPath: {{ .Values.floe.externalPlatformConfig.mountPath | default "/etc/floe/platform.yaml" }}
  subPath: platform.yaml
  readOnly: true
{{- else if .Values.floe.platformSpec.enabled }}
- name: platform-config
  mountPath: {{ .Values.floe.platformSpec.mountPath | default "/app/.floe/platform.yaml" }}
  subPath: platform.yaml
  readOnly: true
{{- end }}
{{- end }}

{{/*
Generate FLOE_PLATFORM_FILE environment variable.
Two-Tier Architecture: Points PlatformResolver to mounted platform.yaml.
*/}}
{{- define "floe-dagster.platformConfigEnv" -}}
{{- if and .Values.floe.externalPlatformConfig.enabled .Values.floe.externalPlatformConfig.setEnvVar }}
- name: FLOE_PLATFORM_FILE
  value: {{ .Values.floe.externalPlatformConfig.mountPath | default "/etc/floe/platform.yaml" }}
{{- else if .Values.floe.platformSpec.enabled }}
- name: FLOE_PLATFORM_FILE
  value: {{ .Values.floe.platformSpec.mountPath | default "/app/.floe/platform.yaml" }}
{{- end }}
{{- end }}
