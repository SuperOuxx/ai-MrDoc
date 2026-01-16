<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import 'luckysheet/dist/plugins/plugins.css'
import 'luckysheet/dist/css/luckysheet.css'
import 'luckysheet/dist/assets/iconfont/iconfont.css'

const props = withDefaults(
  defineProps<{
    modelValue: any[]
  }>(),
  {
    modelValue: () => [
      {
        name: 'Sheet1',
        color: '',
        status: 1,
        order: 0,
        data: [[]],
        column: 20,
        row: 30,
      },
    ],
  }
)

const emits = defineEmits<{
  (e: 'update:modelValue', v: any[]): void
  (e: 'change', v: any[]): void
}>()

const containerId = `luckysheet-${Math.random().toString(36).slice(2)}`
const initialized = ref(false)

const loadSheet = async () => {
  const luckysheet = (await import('luckysheet')).default
  luckysheet.create({
    container: containerId,
    showinfobar: false,
    lang: 'zh',
    data: props.modelValue,
    hook: {
      workbookChange: (data: any) => {
        emits('update:modelValue', data)
        emits('change', data)
      },
    },
  })
  initialized.value = true
}

watch(
  () => props.modelValue,
  () => {
    if (!initialized.value) return
    // Luckysheet lacks light-weight reactive setter; skip to avoid re-render storms.
  }
)

onMounted(loadSheet)
onBeforeUnmount(() => {
  const el = document.getElementById(containerId)
  if (el) el.innerHTML = ''
})
</script>

<template>
  <div class="sheet-shell">
    <div :id="containerId" style="height: 520px; background: #fff; border-radius: 10px; overflow: hidden;" />
  </div>
</template>

<style scoped>
.sheet-shell {
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: var(--shadow);
  overflow: hidden;
  background: #0b1224;
}
</style>
