<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import 'vditor/dist/index.css'

const props = withDefaults(
  defineProps<{
    content: string
  }>(),
  {
    content: '',
  }
)

const container = ref<HTMLDivElement | null>(null)
let renderToken = 0

const renderPreview = async () => {
  const token = ++renderToken
  await nextTick()
  if (!container.value || token !== renderToken) return

  const Vditor = (await import('vditor')).default
  if (!container.value || token !== renderToken) return

  container.value.innerHTML = ''
  container.value.classList.add('vditor-reset')

  const cdnRoot = 'https://unpkg.com/vditor@3.11.2'
  Vditor.preview(container.value, props.content || '', {
    cdn: cdnRoot,
    anchor: 1,
    markdown: { mark: true },
    hljs: { lineNumber: false },
  })
}

watch(
  () => props.content,
  () => {
    renderPreview().catch((err) => {
      console.error('Markdown preview render failed', err)
    })
  }
)

onMounted(() => {
  renderPreview().catch((err) => {
    console.error('Markdown preview init failed', err)
  })
})

onBeforeUnmount(() => {
  renderToken += 1
  if (container.value) {
    container.value.innerHTML = ''
  }
})
</script>

<template>
  <div ref="container" class="doc-preview" />
</template>

<style scoped>
.doc-preview {
  min-height: 120px;
  padding: 8px 2px;
}
</style>
