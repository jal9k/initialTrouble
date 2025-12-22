'use client'

import { useState } from 'react'
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Menu } from 'lucide-react'
import { Sidebar } from './Sidebar'
import type { SidebarProps } from '@/types'

export function MobileSidebar(props: SidebarProps) {
  const [open, setOpen] = useState(false)

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon" className="md:hidden">
          <Menu className="h-5 w-5" />
          <span className="sr-only">Open sidebar</span>
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="p-0 w-72">
        <Sidebar
          {...props}
          onSessionSelect={(id) => {
            props.onSessionSelect(id)
            setOpen(false)
          }}
          onNewSession={() => {
            props.onNewSession()
            setOpen(false)
          }}
          className="w-full border-r-0"
        />
      </SheetContent>
    </Sheet>
  )
}

