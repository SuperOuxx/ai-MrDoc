<script setup lang="ts">
import type { DocNode } from '../types/api'

const props = defineProps<{
  node: DocNode
}>()

const emits = defineEmits<{
  (e: 'open', id: number): void
}>()
</script>

<template>
  <div class="stack" style="gap: 6px; padding-left: 8px; border-left: 1px solid var(--border);">
    <div class="row" style="justify-content: space-between; align-items: center;">
      <span>{{ node.name }}</span>
      <button class="btn" @click="emits('open', node.id)" style="padding: 6px 10px;">查看</button>
    </div>
    <div v-if="node.children && node.children.length" class="stack" style="gap: 6px; padding-left: 10px;">
      <DocTreeNode v-for="c in node.children" :key="c.id" :node="c" @open="emits('open', $event)" />
    </div>
  </div>
</template>
