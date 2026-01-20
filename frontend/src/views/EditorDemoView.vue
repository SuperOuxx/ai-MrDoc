<script setup lang="ts">
import { ref } from 'vue'
import EditorVditor from '../components/EditorVditor.vue'
import EditorEditormd from '../components/EditorEditormd.vue'
import EditorLuckysheet from '../components/EditorLuckysheet.vue'

const vditorContent = ref('# Hello Vditor')
const editormdContent = ref('# Hello Editormd')
const sheetData = ref<any[]>([
  {
    name: 'Sheet1',
    color: '',
    status: 1,
    order: 0,
    data: [
      [{ v: 'Title' }, { v: 'Value' }],
      [{ v: 'A' }, { v: 1 }],
      [{ v: 'B' }, { v: 2 }],
    ],
    column: 10,
    row: 20,
  },
])
</script>

<template>
  <div class="stack" style="gap: 20px;">
    <div class="row" style="justify-content: space-between; align-items: center;">
      <div>
        <h1>Editor Demo</h1>
        <p class="muted">封装 Editormd / Vditor / Luckysheet 组件，后续可对接文档读写接口。</p>
      </div>
    </div>

    <div class="card">
      <h3>Vditor (Markdown/WYSIWYG)</h3>
      <EditorVditor v-model="vditorContent" />
    </div>

    <div class="card">
      <h3>Editormd (Markdown)</h3>
      <EditorEditormd v-model="editormdContent" />
    </div>

    <div class="card">
      <h3>Luckysheet (表格)</h3>
      <EditorLuckysheet v-model="sheetData" />
    </div>
  </div>
</template>
