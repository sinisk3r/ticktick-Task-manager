"use client"

import useSWR from "swr"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Badge } from "@/components/ui/badge"
import { API_BASE } from "@/lib/api"

interface ProjectOption {
  id: number
  name: string
  ticktick_project_id?: string
  color?: string | null
}

interface ProjectSelectorProps {
  value?: number | null
  onChange?: (projectId: number | null, project?: ProjectOption) => void
  placeholder?: string
}

const fetcher = (url: string) => fetch(url).then((r) => r.json())

export function ProjectSelector({ value, onChange, placeholder = "Select project" }: ProjectSelectorProps) {
  const { data, isLoading } = useSWR<ProjectOption[]>(`${API_BASE}/api/projects?user_id=1`, fetcher)
  const options = data || []

  if (isLoading) {
    return <Skeleton className="h-9 w-full" />
  }

  const handleChange = (val: string) => {
    if (val === "none") {
      onChange?.(null, undefined)
      return
    }
    const nextId = Number(val)
    const nextProject = options.find((p) => p.id === nextId)
    onChange?.(nextId, nextProject)
  }

  const currentProject = options.find((p) => p.id === value || p.id === Number(value))

  return (
    <Select value={value ? String(value) : "none"} onValueChange={handleChange}>
      <SelectTrigger className="w-full">
        <SelectValue placeholder={placeholder}>
          {currentProject ? (
            <span className="flex items-center gap-2">
              {currentProject.color && <Badge className="h-2 w-2 p-0 rounded-full" style={{ backgroundColor: currentProject.color }} />}
              {currentProject.name}
            </span>
          ) : (
            placeholder
          )}
        </SelectValue>
      </SelectTrigger>
      <SelectContent align="start" className="z-[100]">
        <SelectItem value="none">No project</SelectItem>
        {options.map((project) => (
          <SelectItem key={project.id} value={String(project.id)}>
            <span className="flex items-center gap-2">
              {project.color && <span className="h-2 w-2 rounded-full" style={{ backgroundColor: project.color }} />}
              {project.name}
              {project.ticktick_project_id && (
                <Badge variant="secondary" className="text-[10px]">
                  TickTick
                </Badge>
              )}
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

