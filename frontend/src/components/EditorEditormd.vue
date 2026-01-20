<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue: string
    placeholder?: string
  }>(),
  { modelValue: '', placeholder: '开始书写 Markdown…' }
)
const emits = defineEmits<{
  (e: 'update:modelValue', v: string): void
  (e: 'change', v: string): void
}>()

const containerId = `editormd-${Math.random().toString(36).slice(2)}`
const editorRef = ref<any>(null)
const loadError = ref('')

const loadScript = (src: string) =>
  new Promise<void>((resolve, reject) => {
    const existing = document.querySelector(`script[src="${src}"]`)
    if (existing) {
      if ((existing as HTMLScriptElement).dataset.loaded === '1') return resolve()
      existing.addEventListener('load', () => resolve(), { once: true })
      existing.addEventListener('error', reject, { once: true })
      return
    }
    const s = document.createElement('script')
    s.src = src
    s.dataset.loaded = '0'
    s.onload = () => {
      s.dataset.loaded = '1'
      resolve()
    }
    s.onerror = reject
    document.body.appendChild(s)
  })

const loadStyle = (href: string) => {
  if (document.querySelector(`link[href="${href}"]`)) return
  const l = document.createElement('link')
  l.rel = 'stylesheet'
  l.href = href
  document.head.appendChild(l)
}

const cdnBases = [
  'https://cdnjs.cloudflare.com/ajax/libs/editor.md/1.5.0',
  'https://cdn.jsdelivr.net/npm/editor.md@1.5.0',
  'https://unpkg.com/editor.md@1.5.0',
]

const tryLoadFromBase = async (base: string) => {
  loadStyle(`${base}/css/editormd.min.css`)
  await loadScript(`${base}/lib/jquery.min.js`)
  if (typeof window !== 'undefined' && window.jQuery) {
    window.$ = window.jQuery
  }
  await loadScript(`${base}/lib/marked.min.js`)
  await loadScript(`${base}/lib/prettify.min.js`)
  await loadScript(`${base}/lib/raphael.min.js`)
  await loadScript(`${base}/lib/underscore.min.js`)
  await loadScript(`${base}/lib/sequence-diagram.min.js`)
  await loadScript(`${base}/lib/flowchart.min.js`)
  await loadScript(`${base}/lib/jquery.flowchart.min.js`)
  await loadScript(`${base}/editormd.min.js`)

  if (!window.editormd) throw new Error('editormd not loaded')

  editorRef.value = window.editormd(containerId, {
    width: '100%',
    height: 500,
    placeholder: props.placeholder,
    markdown: props.modelValue || '',
    path: `${base}/lib/`,
    saveHTMLToTextarea: true,
    watch: false,
    onchange: () => {
      const val = editorRef.value?.getMarkdown?.() || ''
      emits('update:modelValue', val)
      emits('change', val)
    },
  })
}

const init = async () => {
  for (const base of cdnBases) {
    try {
      await tryLoadFromBase(base)
      loadError.value = ''
      return
    } catch (err) {
      console.warn('editormd load failed from', base, err)
      continue
    }
  }
  loadError.value = 'Editormd 资源加载失败，请检查网络或改用 Vditor 模式'
}

watch(
  () => props.modelValue,
  (val) => {
    if (editorRef.value && val !== editorRef.value.getMarkdown()) {
      editorRef.value.setMarkdown(val || '')
    }
  }
)

onMounted(() => {
  init().catch((err) => {
    console.error('Editormd init error', err)
    loadError.value = 'Editormd 资源加载失败'
  })
})
onBeforeUnmount(() => {
  editorRef.value = null
})
</script>

<template>
  <div class="editor-shell">
    <div v-if="loadError" class="muted" style="padding: 12px;">{{ loadError }}</div>
    <div v-else :id="containerId" />
  </div>
</template>

<style scoped>
.editor-shell {
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
  box-shadow: var(--shadow);
}
</style>
