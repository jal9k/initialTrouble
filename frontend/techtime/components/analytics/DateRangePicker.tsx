'use client'

import { useState } from 'react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Popover,
  PopoverContent,
  PopoverTrigger
} from '@/components/ui/popover'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Calendar, ChevronDown } from 'lucide-react'

interface DateRange {
  startDate: Date
  endDate: Date
}

interface DateRangePickerProps {
  value?: DateRange
  onChange: (range: DateRange) => void
  className?: string
}

type PresetKey = '7d' | '30d' | '90d' | '12m' | 'custom'

const presets: Record<PresetKey, { label: string; getDates: () => DateRange }> = {
  '7d': {
    label: 'Last 7 days',
    getDates: () => ({
      startDate: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
      endDate: new Date()
    })
  },
  '30d': {
    label: 'Last 30 days',
    getDates: () => ({
      startDate: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
      endDate: new Date()
    })
  },
  '90d': {
    label: 'Last 90 days',
    getDates: () => ({
      startDate: new Date(Date.now() - 90 * 24 * 60 * 60 * 1000),
      endDate: new Date()
    })
  },
  '12m': {
    label: 'Last 12 months',
    getDates: () => ({
      startDate: new Date(Date.now() - 365 * 24 * 60 * 60 * 1000),
      endDate: new Date()
    })
  },
  custom: {
    label: 'Custom range',
    getDates: () => ({
      startDate: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
      endDate: new Date()
    })
  }
}

function formatDateForInput(date: Date): string {
  return date.toISOString().split('T')[0]
}

function getPresetFromRange(range: DateRange): PresetKey {
  const now = Date.now()
  const startDiff = now - range.startDate.getTime()
  const daysDiff = Math.round(startDiff / (24 * 60 * 60 * 1000))

  if (daysDiff === 7) return '7d'
  if (daysDiff === 30) return '30d'
  if (daysDiff === 90) return '90d'
  if (daysDiff === 365) return '12m'
  return 'custom'
}

export function DateRangePicker({
  value,
  onChange,
  className
}: DateRangePickerProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [selectedPreset, setSelectedPreset] = useState<PresetKey>(
    value ? getPresetFromRange(value) : '30d'
  )
  const [customStart, setCustomStart] = useState(
    value ? formatDateForInput(value.startDate) : formatDateForInput(presets['30d'].getDates().startDate)
  )
  const [customEnd, setCustomEnd] = useState(
    value ? formatDateForInput(value.endDate) : formatDateForInput(new Date())
  )

  const handlePresetChange = (preset: PresetKey) => {
    setSelectedPreset(preset)
    if (preset !== 'custom') {
      const range = presets[preset].getDates()
      setCustomStart(formatDateForInput(range.startDate))
      setCustomEnd(formatDateForInput(range.endDate))
      onChange(range)
    }
  }

  const handleCustomApply = () => {
    const range: DateRange = {
      startDate: new Date(customStart),
      endDate: new Date(customEnd)
    }
    onChange(range)
    setIsOpen(false)
  }

  const displayText = selectedPreset === 'custom'
    ? `${new Date(customStart).toLocaleDateString()} - ${new Date(customEnd).toLocaleDateString()}`
    : presets[selectedPreset].label

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          className={cn('justify-between min-w-[200px]', className)}
        >
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4" />
            <span>{displayText}</span>
          </div>
          <ChevronDown className="h-4 w-4 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80 p-4" align="end">
        <div className="space-y-4">
          {/* Preset selector */}
          <div className="space-y-2">
            <Label>Date Range</Label>
            <Select
              value={selectedPreset}
              onValueChange={(value) => handlePresetChange(value as PresetKey)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select a range" />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(presets).map(([key, { label }]) => (
                  <SelectItem key={key} value={key}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Custom date inputs */}
          {selectedPreset === 'custom' && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1">
                  <Label className="text-xs">Start Date</Label>
                  <Input
                    type="date"
                    value={customStart}
                    onChange={(e) => setCustomStart(e.target.value)}
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">End Date</Label>
                  <Input
                    type="date"
                    value={customEnd}
                    onChange={(e) => setCustomEnd(e.target.value)}
                  />
                </div>
              </div>
              <Button
                onClick={handleCustomApply}
                className="w-full"
                size="sm"
              >
                Apply
              </Button>
            </div>
          )}
        </div>
      </PopoverContent>
    </Popover>
  )
}

