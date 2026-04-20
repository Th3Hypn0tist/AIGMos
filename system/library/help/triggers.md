# Triggers

## What `!` is

`!` is a trigger object.

A trigger is a condition / pulse / gating object that decides whether something should fire.

## Relationship to events

- trigger decides when
- event decides what command dispatch happens

## What a trigger is not

- not the command itself
- not the event itself
- not a runner loop

## Mental model

```text
state/input changes -> trigger condition changes -> event may be emitted
```
