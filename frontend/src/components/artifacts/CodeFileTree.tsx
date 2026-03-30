import { useState } from "react"
import { File, Folder, FolderOpen } from "lucide-react"
import { cn } from "@/lib/utils"
import type { CodeFileInfo } from "@/api/types"

interface TreeNode {
  name: string
  path: string
  isDir: boolean
  children: TreeNode[]
  file?: CodeFileInfo
}

function buildTree(files: CodeFileInfo[]): TreeNode[] {
  const root: TreeNode[] = []

  for (const file of files) {
    const parts = file.path.split("/")
    let current = root

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i]
      const isFile = i === parts.length - 1
      const existingNode = current.find((n) => n.name === part)

      if (existingNode) {
        if (isFile) {
          existingNode.file = file
        }
        current = existingNode.children
      } else {
        const newNode: TreeNode = {
          name: part,
          path: parts.slice(0, i + 1).join("/"),
          isDir: !isFile,
          children: [],
          file: isFile ? file : undefined,
        }
        current.push(newNode)
        current = newNode.children
      }
    }
  }

  // Sort: directories first, then files
  function sortTree(nodes: TreeNode[]) {
    nodes.sort((a, b) => {
      if (a.isDir !== b.isDir) return a.isDir ? -1 : 1
      return a.name.localeCompare(b.name)
    })
    for (const node of nodes) {
      sortTree(node.children)
    }
  }
  sortTree(root)
  return root
}

interface CodeFileTreeProps {
  files: CodeFileInfo[]
  selectedPath: string | null
  onSelect: (file: CodeFileInfo) => void
}

export function CodeFileTree({ files, selectedPath, onSelect }: CodeFileTreeProps) {
  const tree = buildTree(files)

  if (files.length === 0) {
    return <p className="text-sm text-muted-foreground py-4">No code files.</p>
  }

  return (
    <div className="text-sm">
      {tree.map((node) => (
        <TreeItem
          key={node.path}
          node={node}
          depth={0}
          selectedPath={selectedPath}
          onSelect={onSelect}
        />
      ))}
    </div>
  )
}

function TreeItem({
  node,
  depth,
  selectedPath,
  onSelect,
}: {
  node: TreeNode
  depth: number
  selectedPath: string | null
  onSelect: (file: CodeFileInfo) => void
}) {
  const [expanded, setExpanded] = useState(true)

  if (node.isDir) {
    return (
      <div>
        <button
          className="flex w-full items-center gap-1.5 rounded px-1 py-0.5 hover:bg-muted/50"
          style={{ paddingLeft: `${depth * 16 + 4}px` }}
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? (
            <FolderOpen className="h-4 w-4 text-amber-500" />
          ) : (
            <Folder className="h-4 w-4 text-amber-500" />
          )}
          <span>{node.name}</span>
        </button>
        {expanded && node.children.map((child) => (
          <TreeItem
            key={child.path}
            node={child}
            depth={depth + 1}
            selectedPath={selectedPath}
            onSelect={onSelect}
          />
        ))}
      </div>
    )
  }

  const isSelected = selectedPath === node.file?.path
  return (
    <button
      className={cn(
        "flex w-full items-center gap-1.5 rounded px-1 py-0.5 hover:bg-muted/50",
        isSelected && "bg-accent text-accent-foreground",
      )}
      style={{ paddingLeft: `${depth * 16 + 4}px` }}
      onClick={() => node.file && onSelect(node.file)}
    >
      <File className="h-4 w-4 text-muted-foreground" />
      <span className="truncate">{node.name}</span>
    </button>
  )
}
