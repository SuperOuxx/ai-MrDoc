export interface ApiResponse<T> {
  code: number
  data: T
  msg: string
}

export interface Pagination<T> {
  results: T[]
  page: number
  page_size: number
  count: number
  total_pages: number
}

export interface Project {
  id: number
  name: string
  intro: string
  role: number
  role_value: string | null
  is_top: boolean
  doc_count?: number
  collaborator_count?: number
  modify_time?: string
}

export interface Doc {
  id: number
  name: string
  pre_content?: string | null
  content?: string | null
  top_doc: number
  parent_doc: number
  status: number
  editor_mode: number
  modify_time?: string
}

export interface DocNode {
  id: number
  name: string
  children?: DocNode[]
}

export interface DocShare {
  id: number
  token: string | null
  share_type: number
  share_value: string | null
  is_enable: boolean
  create_time: string
}

export interface LoginPayload {
  username: string
  password: string
}

export interface LoginResult {
  refresh: string
  access: string
  user: {
    id: number
    username: string
    email?: string
    is_superuser: boolean
    is_staff: boolean
    first_name?: string
    last_name?: string
  }
}
