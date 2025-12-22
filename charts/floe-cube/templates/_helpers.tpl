{{/*
Helm template helpers for floe-cube chart.

These templates provide common functions for:
- Generating consistent resource names
- Creating standard labels and selectors
- Building image references

Covers: 007-FR-001 (Helm chart for Kubernetes deployment)
*/}}

{{/*
Expand the name of the chart.
*/}}
{{- define "floe-cube.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "floe-cube.fullname" -}}
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
{{- define "floe-cube.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels for all resources.
*/}}
{{- define "floe-cube.labels" -}}
helm.sh/chart: {{ include "floe-cube.chart" . }}
{{ include "floe-cube.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: floe-runtime
{{- end }}

{{/*
Selector labels for pod matching - API component.
*/}}
{{- define "floe-cube.selectorLabels" -}}
app.kubernetes.io/name: {{ include "floe-cube.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Selector labels for API server.
*/}}
{{- define "floe-cube.api.selectorLabels" -}}
{{ include "floe-cube.selectorLabels" . }}
app.kubernetes.io/component: api
{{- end }}

{{/*
Selector labels for refresh worker.
*/}}
{{- define "floe-cube.refreshWorker.selectorLabels" -}}
{{ include "floe-cube.selectorLabels" . }}
app.kubernetes.io/component: refresh-worker
{{- end }}

{{/*
Selector labels for Cube store.
*/}}
{{- define "floe-cube.cubeStore.selectorLabels" -}}
{{ include "floe-cube.selectorLabels" . }}
app.kubernetes.io/component: cube-store
{{- end }}

{{/*
Create the name of the service account to use.
*/}}
{{- define "floe-cube.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "floe-cube.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Generate image reference with tag defaulting to appVersion.
*/}}
{{- define "floe-cube.image" -}}
{{- $tag := default .Chart.AppVersion .Values.api.image.tag }}
{{- printf "%s:%s" .Values.api.image.repository $tag }}
{{- end }}

{{/*
Generate the ConfigMap name for Cube schema.
*/}}
{{- define "floe-cube.schemaConfigMapName" -}}
{{- include "floe-cube.fullname" . }}-schema
{{- end }}

{{/*
Generate the ConfigMap name for CompiledArtifacts.
*/}}
{{- define "floe-cube.compiledArtifactsConfigMapName" -}}
{{- if .Values.floe.compiledArtifacts.configMapName }}
{{- .Values.floe.compiledArtifacts.configMapName }}
{{- else }}
{{- include "floe-cube.fullname" . }}-compiled-artifacts
{{- end }}
{{- end }}

{{/*
Common environment variables for Cube components.
*/}}
{{- define "floe-cube.env" -}}
- name: CUBEJS_DEV_MODE
  value: {{ .Values.devMode | default "false" | quote }}
- name: CUBEJS_DB_TYPE
  value: {{ .Values.database.type | quote }}
- name: CUBEJS_SCHEMA_PATH
  value: {{ .Values.floe.schemaPath | quote }}
{{- if .Values.floe.compiledArtifacts.enabled }}
- name: FLOE_COMPILED_ARTIFACTS_PATH
  value: {{ .Values.floe.compiledArtifacts.mountPath | quote }}
{{- end }}
{{/*
Pre-aggregation configuration
*/}}
- name: CUBEJS_EXTERNAL_DEFAULT
  value: {{ .Values.preAggregations.external | default true | quote }}
{{- if .Values.preAggregations.scheduledRefresh.enabled }}
- name: CUBEJS_SCHEDULED_REFRESH_DEFAULT
  value: "true"
- name: CUBEJS_SCHEDULED_REFRESH_TIMEZONE
  value: {{ .Values.preAggregations.scheduledRefresh.timezone | default "UTC" | quote }}
{{- end }}
{{/*
Export bucket configuration (for large pre-aggregation builds)
*/}}
{{- if .Values.preAggregations.exportBucket.enabled }}
- name: CUBEJS_DB_EXPORT_BUCKET_TYPE
  value: {{ .Values.preAggregations.exportBucket.type | quote }}
- name: CUBEJS_DB_EXPORT_BUCKET
  value: {{ .Values.preAggregations.exportBucket.name | quote }}
{{- if .Values.preAggregations.exportBucket.region }}
- name: CUBEJS_DB_EXPORT_BUCKET_AWS_REGION
  value: {{ .Values.preAggregations.exportBucket.region | quote }}
{{- end }}
{{- if .Values.preAggregations.exportBucket.secretName }}
- name: CUBEJS_DB_EXPORT_BUCKET_AWS_KEY
  valueFrom:
    secretKeyRef:
      name: {{ .Values.preAggregations.exportBucket.secretName | quote }}
      key: {{ .Values.preAggregations.exportBucket.accessKeyKey | quote }}
- name: CUBEJS_DB_EXPORT_BUCKET_AWS_SECRET
  valueFrom:
    secretKeyRef:
      name: {{ .Values.preAggregations.exportBucket.secretName | quote }}
      key: {{ .Values.preAggregations.exportBucket.secretKeyKey | quote }}
{{- end }}
{{- if .Values.preAggregations.exportBucket.integration }}
- name: CUBEJS_DB_EXPORT_INTEGRATION
  value: {{ .Values.preAggregations.exportBucket.integration | quote }}
{{- end }}
{{- end }}
{{/*
Cube Store S3 configuration
*/}}
{{- if and .Values.cubeStore.enabled .Values.cubeStore.s3.bucket }}
- name: CUBEJS_EXT_DB_TYPE
  value: "cubestore"
- name: CUBEJS_CUBESTORE_S3_BUCKET
  value: {{ .Values.cubeStore.s3.bucket | quote }}
{{- if .Values.cubeStore.s3.region }}
- name: CUBEJS_CUBESTORE_S3_REGION
  value: {{ .Values.cubeStore.s3.region | quote }}
{{- end }}
{{- if .Values.cubeStore.s3.endpoint }}
- name: CUBEJS_CUBESTORE_S3_ENDPOINT
  value: {{ .Values.cubeStore.s3.endpoint | quote }}
{{- end }}
{{- if .Values.cubeStore.s3.secretName }}
- name: CUBEJS_CUBESTORE_AWS_ACCESS_KEY_ID
  valueFrom:
    secretKeyRef:
      name: {{ .Values.cubeStore.s3.secretName | quote }}
      key: {{ .Values.cubeStore.s3.accessKeyKey | quote }}
- name: CUBEJS_CUBESTORE_AWS_SECRET_ACCESS_KEY
  valueFrom:
    secretKeyRef:
      name: {{ .Values.cubeStore.s3.secretName | quote }}
      key: {{ .Values.cubeStore.s3.secretKeyKey | quote }}
{{- end }}
{{- end }}
{{- end }}
