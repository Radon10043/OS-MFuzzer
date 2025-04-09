// Copyright 2024 syzkaller project authors. All rights reserved.
// Use of this source code is governed by Apache 2 LICENSE that can be found in the LICENSE file.

package fuzzer

import (
	"sync"

	"github.com/google/syzkaller/pkg/signal"
	"github.com/google/syzkaller/pkg/stat"
)

// Cover keeps track of the signal known to the fuzzer.
type Cover struct {
	mu        sync.RWMutex
	maxSignal signal.Signal // max signal ever observed (including flakes)
	newSignal signal.Signal // newly identified max signal
}

func newCover() *Cover {
	cover := new(Cover)
	stat.New("max signal", "Maximum fuzzing signal (including flakes)",
		stat.Graph("signal"), stat.LenOf(&cover.maxSignal, &cover.mu))
	return cover
}

// Signal that should no longer be chased after.
// It is not returned in GrabSignalDelta().
func (cover *Cover) AddMaxSignal(sign signal.Signal) {
	cover.mu.Lock()
	defer cover.mu.Unlock()
	cover.maxSignal.Merge(sign)
}

func (cover *Cover) addRawMaxSignal(signal []uint64, prio uint8) signal.Signal {
	cover.mu.Lock()
	defer cover.mu.Unlock()
	diff := cover.maxSignal.DiffRaw(signal, prio)
	if diff.Empty() {
		return diff
	}
	cover.maxSignal.Merge(diff)
	cover.newSignal.Merge(diff)
	return diff
}

func (cover *Cover) CopyMaxSignal() signal.Signal {
	cover.mu.RLock()
	defer cover.mu.RUnlock()
	return cover.maxSignal.Copy()
}

func (cover *Cover) GrabSignalDelta() signal.Signal {
	cover.mu.Lock()
	defer cover.mu.Unlock()
	plus := cover.newSignal
	cover.newSignal = nil
	return plus
}

// MetaCover keeps track of the signal known to the metamorhic binary.
type MetaCover struct {
	mu        sync.RWMutex
	maxSignal signal.Signal
}

func newMetaCover() *MetaCover {
	metaCover := new(MetaCover)
	stat.New("max signal", "Maximum fuzzing signal (including flakes)",
		stat.Graph("signal"), stat.LenOf(&metaCover.maxSignal, &metaCover.mu))
	return metaCover
}

// Merge the new signal into the max signal and get differences between them.
func (metaCover *MetaCover) addRawMaxSignal(signal []uint64, prio uint8) signal.Signal {
	metaCover.mu.Lock()
	defer metaCover.mu.Unlock()
	diff := metaCover.maxSignal.DiffRaw(signal, prio)
	if diff.Empty() {
		return diff
	}
	metaCover.maxSignal.Merge(diff)
	return diff
}

// Get the exclusive signals of the metamorphic binary.
func (metaCover *MetaCover) exclusiveSignals(cover *Cover) signal.Signal {
	metaCover.mu.RLock()
	defer metaCover.mu.RUnlock()
	cover.mu.RLock()
	defer cover.mu.RUnlock()

	// Traverse MetaCover, find signals that are not in fuzzing cover.
	var diff signal.Signal
	for e, p := range metaCover.maxSignal {
		if _, ok := cover.maxSignal[e]; ok {
			continue
		}
		if diff == nil {
			diff = make(signal.Signal)
		}
		diff[e] = p
	}

	return diff
}
