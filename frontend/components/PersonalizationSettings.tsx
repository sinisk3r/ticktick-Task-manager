"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { API_BASE } from "@/lib/api"

export function PersonalizationSettings() {
  const [peopleText, setPeopleText] = useState("")
  const [petsText, setPetsText] = useState("")
  const [activitiesText, setActivitiesText] = useState("")
  const [notesText, setNotesText] = useState("")
  const [profileMessage, setProfileMessage] = useState("")
  const [profileLoading, setProfileLoading] = useState(false)
  const [profileSaving, setProfileSaving] = useState(false)
  const [backendUrl] = useState(API_BASE)

  const parseList = (text: string) =>
    text
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
  const listToText = (items?: string[]) => (items && items.length ? items.join("\n") : "")

  useEffect(() => {
    loadProfile()
  }, [])

  const loadProfile = async () => {
    setProfileLoading(true)
    try {
      const response = await fetch(`${backendUrl}/api/profile?user_id=1`)
      if (response.ok) {
        const data = await response.json()
        setPeopleText(listToText(data.people))
        setPetsText(listToText(data.pets))
        setActivitiesText(listToText(data.activities))
        setNotesText(data.notes || "")
      }
    } catch (err) {
      console.error("Failed to load profile:", err)
      setProfileMessage("Unable to load personal context")
    } finally {
      setProfileLoading(false)
    }
  }

  const saveProfile = async () => {
    setProfileSaving(true)
    setProfileMessage("")
    try {
      const payload = {
        people: parseList(peopleText),
        pets: parseList(petsText),
        activities: parseList(activitiesText),
        notes: notesText.trim() || null,
      }
      const response = await fetch(`${backendUrl}/api/profile?user_id=1`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
      if (response.ok) {
        setProfileMessage("Personal context saved")
      } else {
        setProfileMessage("Failed to save personal context")
      }
    } catch (err) {
      console.error("Failed to save profile:", err)
      setProfileMessage("Failed to save personal context")
    } finally {
      setProfileSaving(false)
      setTimeout(() => setProfileMessage(""), 3000)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Personal Context</CardTitle>
        <CardDescription>
          Share concise details to help the LLM personalize analysis (kept short for optimal results)
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">People & roles</label>
            <Textarea
              placeholder={"Sam (manager)\nAlex (partner)"}
              value={peopleText}
              onChange={(e) => setPeopleText(e.target.value)}
              rows={4}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Pets</label>
            <Textarea
              placeholder={"Ari (cat)"}
              value={petsText}
              onChange={(e) => setPetsText(e.target.value)}
              rows={4}
            />
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Activities</label>
          <Textarea
            placeholder={"Climbing Tue/Thu\nYoga Sat"}
            value={activitiesText}
            onChange={(e) => setActivitiesText(e.target.value)}
            rows={3}
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Notes</label>
          <Textarea
            placeholder="Morning focus time, prefers async updates"
            value={notesText}
            onChange={(e) => setNotesText(e.target.value)}
            rows={3}
          />
        </div>

        <div className="flex items-center gap-3">
          <Button onClick={saveProfile} disabled={profileSaving || profileLoading}>
            {profileSaving ? "Saving..." : "Save personal context"}
          </Button>
          {profileMessage && <span className="text-sm text-muted-foreground">{profileMessage}</span>}
          {profileLoading && <span className="text-xs text-muted-foreground">Loading...</span>}
        </div>
        <p className="text-xs text-muted-foreground">
          We store this securely and send a compressed summary with each analysis. Keep it brief for best results.
        </p>
      </CardContent>
    </Card>
  )
}
