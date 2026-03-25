import { OpenVidu } from 'openvidu-browser';
import { useRef, useState } from 'react';
import api from '../services/api';

export function useOpenVidu() {
  const OV = useRef(null);
  const session = useRef(null);
  const [participants, setParticipants] = useState({});

  async function joinMeeting(displayName, sessionId) {
    OV.current = new OpenVidu();
    session.current = OV.current.initSession();

    // Uzak stream geldiğinde — her stream ayrı participant
    session.current.on('streamCreated', async (event) => {
      const subscriber = session.current.subscribe(event.stream, undefined);
      let connectionData = {};
      try {
           connectionData = JSON.parse(event.stream.connection.data);
      } catch(e) {
           console.log("Could not parse connection data.");
      }
      const participantId = connectionData.participant_id || event.stream.connection.connectionId;

      try {
          // Backend'e stream_id güncelle
          await api.patch(`/participants/${participantId}/stream`, {
            stream_id: event.stream.streamId,
            connection_id: event.stream.connection.connectionId
          });
      } catch (err) {
         console.warn("Failed to patch stream info to backend", err);
      }

      setParticipants(prev => ({
        ...prev,
        [participantId]: { subscriber, stream: event.stream, displayName: connectionData.display_name || "Unknown" }
      }));
    });

    session.current.on('streamDestroyed', (event) => {
      try {
          const data = JSON.parse(event.stream.connection.data);
          setParticipants(prev => {
            const next = {...prev};
            delete next[data.participant_id];
            return next;
          });
      } catch (e) {
          console.warn("Could not handle streamDestroyed connection data");
      }
    });

    // Token al ve bağlan
    const { token, participant_id } = await api.post('/sessions/token', {
      session_id: sessionId,
      display_name: displayName,
      device_info: getDeviceInfo()
    });

    await session.current.connect(token, 
      JSON.stringify({ participant_id, display_name: displayName }));

    // Yayın başlat
    const publisher = await OV.current.initPublisherAsync(undefined, {
      audioSource: undefined,
      videoSource: false,      // sadece ses
      publishAudio: true,
      publishVideo: false
    });

    await session.current.publish(publisher);
    return participant_id;
  }

  function getDeviceInfo() {
    const ua = navigator.userAgent;
    return {
      browser: /Chrome/.test(ua) ? 'chrome' : /Firefox/.test(ua) ? 'firefox' : 'other',
      os: /Android/.test(ua) ? 'android' : /iPhone|iPad/.test(ua) ? 'ios' :
          /Windows/.test(ua) ? 'windows' : 'macos',
      device_type: /Mobi|Android/i.test(ua) ? 'mobile' : 'desktop'
    };
  }

  return { joinMeeting, participants, session };
}
