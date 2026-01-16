<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch, nextTick } from 'vue'
import 'vditor/dist/index.css'

const props = withDefaults(
  defineProps<{
    modelValue: string
    placeholder?: string
  }>(),
  { modelValue: '', placeholder: '开始书写...' }
)

const emits = defineEmits<{
  (e: 'update:modelValue', v: string): void
  (e: 'change', v: string): void
}>()

const el = ref<HTMLDivElement | null>(null)
const domId = `vditor-${Math.random().toString(36).slice(2)}`
let editor: any = null
let isDestroyed = false

const init = async () => {
  if (!el.value || isDestroyed) return
  await nextTick()
  if (!el.value || isDestroyed) return

  try {
    const Vditor = (await import('vditor')).default

    // Use unpkg CDN for all Vditor resources
    // Using 'ir' (instant rendering) mode instead of 'wysiwyg' for better stability
    // IR mode is Vditor's recommended mode (Typora-like experience)
    const cdnRoot = 'https://unpkg.com/vditor@3.11.2'

    editor = new Vditor(el.value, {
      mode: 'ir',  // Changed from 'wysiwyg' to 'ir' for better stability
      placeholder: props.placeholder,
      height: 520,
      cdn: cdnRoot,
      lang: 'zh_CN',
      toolbar: [
        'headings',
        'bold',
        'italic',
        'strike',
        '|',
        'list',
        'ordered-list',
        'check',
        'quote',
        '|',
        'code',
        'inline-code',
        'table',
        'line',
        '|',
        'link',
        'upload',
        '|',
        'undo',
        'redo',
        '|',
        'edit-mode',
        'fullscreen',
        'outline',
      ],
      cache: { enable: false },
      after: () => {
        if (editor && props.modelValue && !isDestroyed) {
          editor.setValue(props.modelValue)
        }
      },
      input: (value: string) => {
        if (!isDestroyed) {
          emits('update:modelValue', value)
          emits('change', value)
        }
      },
    })
  } catch (err) {
    console.error('Vditor initialization error:', err)
  }
}

watch(
  () => props.modelValue,
  (val) => {
    if (editor && !isDestroyed && val !== editor.getValue()) {
      editor.setValue(val || '')
    }
  }
)

onMounted(init)

onBeforeUnmount(() => {
  isDestroyed = true
  if (editor) {
    try {
      if (editor.destroy) {
        editor.destroy()
      }
    } catch (err) {
      console.error('Vditor destroy error:', err)
    }
    editor = null
  }
})
</script>

<template>
  <div class="editor-shell">
    <div :id="domId" ref="el" />
  </div>
</template>

<style scoped>
.editor-shell :deep(.vditor) {
  border-radius: 12px;
  border: 1px solid var(--border);
  box-shadow: var(--shadow);
}
</style>
