<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  show: boolean
  projectId: number | null
}>()
const emits = defineEmits<{
  (e: 'submit', code: string): void
  (e: 'close'): void
}>()

const code = ref('')

watch(
  () => props.show,
  (val) => {
    if (val) code.value = ''
  }
)

const handleSubmit = () => {
  if (!code.value.trim()) return
  emits('submit', code.value.trim())
}
</script>

<template>
  <div v-if="show" class="modal-backdrop">
    <div class="modal">
      <div class="row" style="justify-content: space-between; align-items: center;">
        <h3>Access Code Required</h3>
        <button class="btn" @click="emits('close')">Close</button>
      </div>
      <p class="muted">请输入访问码以查看该文档或文集。</p>
      <div class="stack">
        <input class="input" v-model="code" placeholder="访问码" />
        <div class="hint">文集 ID: {{ projectId ?? '-' }}</div>
        <button class="btn primary" @click="handleSubmit">提交</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: grid;
  place-items: center;
  z-index: 50;
}
.modal {
  width: min(420px, 92vw);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 20px;
  box-shadow: var(--shadow);
}
</style>
